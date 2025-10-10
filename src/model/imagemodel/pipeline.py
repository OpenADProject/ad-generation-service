# =======================================
# pipeline.py — 최종 완성본 (Full Code)
# =======================================
# 모든 지능형 기능 및 안정성 개선이 포함된 최종 버전
# =======================================

import os
import io
import base64
import logging
import json
import torch
import torch.nn.functional as F
import numpy as np
import cv2
from PIL import Image

from rembg import remove

import config
from transformers import CLIPVisionModelWithProjection, GroundingDinoProcessor, AutoModelForZeroShotObjectDetection
from diffusers import (
    StableDiffusionXLPipeline,
    StableDiffusionXLControlNetPipeline, 
    StableDiffusionXLImg2ImgPipeline,
    ControlNetModel,
    AutoencoderKL
)
from prompt_utils import encode_prompt_sdxl, build_ad_prompt_compose, get_relative_scale_from_llm, _get_product_category_from_llm

def _clip_text_embed(pipe, text: str):
    te = getattr(pipe, "text_encoder_2", None) or getattr(pipe, "text_encoder", None)
    tok = getattr(pipe, "tokenizer_2", None) or getattr(pipe, "tokenizer", None)
    if te is None or tok is None: raise RuntimeError("No text encoder/tokenizer on pipeline")
    inputs = tok(text, return_tensors="pt", padding=True, truncation=True, max_length=tok.model_max_length).to(pipe.device)
    with torch.no_grad():
        out = te(**inputs, output_hidden_states=True)
        pooled = out[0]
    return F.normalize(pooled, dim=-1)

def _intent_action_score(pipe, user_text: str) -> float:
    act_refs = ["subject physically holding the product", "clear hand or paw gripping the item", "tactile interaction"]
    static_refs = ["static studio product photo", "product centered, model nearby but not touching"]
    q = _clip_text_embed(pipe, user_text)
    act = F.normalize(torch.stack([_clip_text_embed(pipe, t).squeeze(0) for t in act_refs], dim=0).mean(dim=0, keepdim=True), dim=-1)
    sta = F.normalize(torch.stack([_clip_text_embed(pipe, t).squeeze(0) for t in static_refs], dim=0).mean(dim=0, keepdim=True), dim=-1)
    s_act, s_sta = float((q @ act.T).squeeze()), float((q @ sta.T).squeeze())
    return max(0.0, min(1.0, (s_act - s_sta) * 0.5 + 0.5))

class OutputManager:
    def __init__(self, output_dir="outputs", logger=None):
        self.output_dir, self.logger = output_dir, logger or logging.getLogger("AdImagePipeline")
        os.makedirs(self.output_dir, exist_ok=True)
    def save(self, image: Image.Image, base_filename: str) -> str:
        path = os.path.join(self.output_dir, f"{base_filename}.png")
        image.save(path)
        if self.logger: self.logger.info(f"Image saved to {path}")
        return path
    def to_base64(self, image: Image.Image) -> str:
        buf = io.BytesIO()
        image.save(buf, format="PNG"); return base64.b64encode(buf.getvalue()).decode("utf-8")

class ModelManager:
    def __init__(self, config, logger):
        self.config, self.logger, self.loaded_models = config, logger, {}

    def load_model(self, key, model_class, model_path, **kwargs):
        if key in self.loaded_models: return self.loaded_models[key]
        self.logger.info(f"Loading model '{key}' from {model_path}...")
        
        use_fp16 = kwargs.pop('use_fp16_variant', False)
        pretrained_kwargs = {"torch_dtype": self.config.TORCH_DTYPE, "use_safetensors": True, **kwargs}
        if use_fp16: pretrained_kwargs["variant"] = "fp16"
        
        model = model_class.from_pretrained(model_path, **pretrained_kwargs)

        if hasattr(model, "to"):
            model.to(self.config.DEVICE)
            
        self.loaded_models[key] = model
        return model

    def unload(self, *keys):
        keys_to_unload = keys or list(self.loaded_models.keys())
        for k in keys_to_unload:
            if k in self.loaded_models:
                del self.loaded_models[k]
                self.logger.info(f"Model '{k}' unloaded.")

class ImageGenerationPipeline:
    def __init__(self, config, logger):
        self.config, self.logger = config, logger
        self.model_manager = ModelManager(config, logger)
        
        self.negative_prompt = (
            "ugly, deformed, noisy, blurry, low resolution, bad anatomy, "
            "poorly drawn face, poorly drawn hands, missing limbs, "
            "extra limbs, fused fingers, too many fingers, "
            "watermark, signature, text, copyright, "
            "visible studio equipment, light stands, softboxes, tripods, "
            "photography gear, cables, wires, studio backdrop edges, "
            "clutter, distractions, messy, dirty, dark, sad, crying"
        )
        
        try:
            if hasattr(config, 'REMBG_MODEL_PATH') and config.REMBG_MODEL_PATH:
                import onnxruntime
                self.rembg_session = onnxruntime.InferenceSession(config.REMBG_MODEL_PATH, providers=['CPUExecutionProvider'])
            else:
                self.rembg_session = None
        except Exception as e:
            self.logger.warning(f"Could not load rembg onnx session, will use default session: {e}")
            self.rembg_session = None

        self.templates = {}
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(current_dir, "templates.json")
            with open(template_path, "r", encoding="utf-8") as f:
                self.templates = json.load(f)
            self.logger.info(f"Templates loaded successfully from {template_path}.")
        except Exception as e:
            self.logger.warning(f"Could not load templates.json: {e}. Using a fallback template.")
            self.templates["white_default"] = {"name": "화이트(기본)"}

    def _get_box(self, image: Image.Image, text_prompt: str, model_key_suffix: str) -> list[int] | None:
        self.logger.info(f"Analyzing image to find '{text_prompt}'...")
        try:
            processor = self.model_manager.load_model(f"dino_processor_{model_key_suffix}", GroundingDinoProcessor, self.config.GROUNDING_DINO_PATH)
            model = self.model_manager.load_model(f"dino_model_{model_key_suffix}", AutoModelForZeroShotObjectDetection, self.config.GROUNDING_DINO_PATH, torch_dtype=torch.float32)
            
            inputs = processor(images=image, text=text_prompt, return_tensors="pt").to(self.config.DEVICE)
            with torch.no_grad():
                outputs = model(**inputs)
            
            original_size = image.size
            target_sizes = torch.tensor([original_size[::-1]]).to(self.config.DEVICE)
            results = processor.image_processor.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=0.3)[0]

            if len(results["boxes"]) > 0:
                best_box = results["boxes"][0].cpu().numpy().astype(int)
                self.logger.info(f"'{text_prompt}' area found at coordinates: {best_box.tolist()}")
                return best_box.tolist()
            else:
                self.logger.warning(f"No suitable area for '{text_prompt}' found by Grounding DINO.")
                return None
        except Exception as e:
            self.logger.error(f"Error during '{text_prompt}' analysis with Grounding DINO: {e}")
            return None
        finally:
            self.model_manager.unload(f"dino_processor_{model_key_suffix}", f"dino_model_{model_key_suffix}")

    def _create_composite_ip_image(self, model_image, product_image, base_image: Image.Image, interaction_detected: bool, relative_scale: float):
        self.logger.info("Compositing subjects onto the background...")
        try:
            width, height = base_image.size
            canvas = base_image.copy().convert("RGBA")
            temp_canvas = Image.new("RGBA", (width, height), (0,0,0,0))

            model_fg = remove(model_image, session=self.rembg_session) if model_image else None
            product_fg = remove(product_image, session=self.rembg_session) if product_image else None

            if model_fg: model_fg.thumbnail((int(width * 0.95), int(height * 0.95)), Image.LANCZOS)
            
            if product_fg:
                if model_fg and model_fg.height > 0:
                    target_product_height = int(model_fg.height * relative_scale)
                    if product_fg.height > 0:
                        ratio = target_product_height / product_fg.height
                        target_product_width = int(product_fg.width * ratio)
                        if target_product_width > 0 and target_product_height > 0:
                            product_fg = product_fg.resize((target_product_width, target_product_height), Image.LANCZOS)
                else:
                    product_fg.thumbnail((int(width * 0.5), int(height * 0.5)), Image.LANCZOS)

            m_x, m_y = 0, 0
            if model_fg:
                m_x = (width - model_fg.width) // 2
                m_y = height - model_fg.height
                temp_canvas.paste(model_fg, (m_x, m_y), model_fg)

            if product_fg:
                p_x, p_y = 0, 0
                if model_fg and interaction_detected:
                    hands_box = self._get_box(model_image, "a person's hands or animal's paws", "paws_placement")
                    if hands_box:
                        self.logger.info("Placing product near detected hands or paws.")
                        hands_center_x = (hands_box[0] + hands_box[2]) // 2
                        hands_center_y = (hands_box[1] + hands_box[3]) // 2
                        p_x = hands_center_x - product_fg.width // 2
                        p_y = hands_center_y - int(product_fg.height * 0.8)
                    else:
                        self.logger.warning("Could not find hands/paws, placing product at model's lower center as a fallback.")
                        p_x = m_x + (model_fg.width - product_fg.width) // 2
                        p_y = m_y + int(model_fg.height * 0.6)
                else:
                    placement_box = self._get_box(base_image, "the floor or the ground or a table", "bg_placement")
                    if placement_box:
                        box_center_x = (placement_box[0] + placement_box[2]) // 2
                        surface_top_y = placement_box[1]
                        p_x = box_center_x - product_fg.width // 2
                        p_y = surface_top_y - product_fg.height
                    else:
                        p_x = (width - product_fg.width) // 2
                        p_y = height - product_fg.height
                
                p_x = max(0, min(p_x, width - product_fg.width))
                p_y = max(0, min(p_y, height - product_fg.height))
                temp_canvas.paste(product_fg, (p_x, p_y), product_fg)
            
            final_image = Image.alpha_composite(canvas, temp_canvas)
            return final_image.convert("RGB")
        except Exception as e:
            self.logger.error(f"Failed to create composite image: {e}")
            return base_image

    def _prepare_canny_image(self, image: Image.Image, low_threshold=100, high_threshold=200):
        self.logger.info("Preparing Canny edge image for ControlNet...")
        image_np = np.array(image)
        canny_image_np = cv2.Canny(image_np, low_threshold, high_threshold)
        canny_image_np = np.stack([canny_image_np] * 3, axis=-1)
        return Image.fromarray(canny_image_np)

    def run(self, inputs):
        base_output_dir = "outputs"
        os.makedirs(base_output_dir, exist_ok=True)
        run_id = max(map(int, [d for d in os.listdir(base_output_dir) if d.isdigit()]), default=0) + 1
        run_output_dir = os.path.join(base_output_dir, str(run_id))
        output_manager = OutputManager(output_dir=run_output_dir, logger=self.logger)
        self.logger.info(f"Output for this run will be saved to: {run_output_dir}")
        
        ad_prompt = None
        base_image_latents = None
        pipe = None
        
        try:
            params = inputs.get("params", {})
            prompt_text = inputs.get("prompt")
            product_image_b64 = inputs.get("product_image")
            
            product_image = self._load_b64(product_image_b64)
            model_image = self._load_b64(inputs.get("model_image"))

            width, height = map(int, params.get("size", "1024x1024").split("x"))
            seed = int(params.get("seed")) if params.get("seed") is not None else torch.randint(0, 2**32-1, (1,)).item()
            generator = torch.Generator(device=self.config.DEVICE).manual_seed(seed)
            self.logger.info(f"Input loaded. Size: {width}x{height}, Seed: {seed}")

            try:
                self.logger.info("Automatically detecting product category...")
                product_category = _get_product_category_from_llm(
                    prompt_text,
                    product_image_b64,
                    self.config.OPENAI_API_KEY,
                    self.logger
                )
                    if product_fg:
                is_interaction_forced = (subject_image is not None)

                if not is_for_canny_map and is_interaction_forced:
                    self.logger.info("IP-Adapter mode: Subject exists, attempting to place product near paws.")
                    paws_box = self._get_box(subject_image, "animal's paws or feet", "paws_placement", processor=dino_processor, model=dino_model)
                    
                    if paws_box:
                        self.logger.info("Paws detected. Placing product centered above the paws.")
                        paws_center_x = (paws_box[0] + paws_box[2]) // 2
                        paws_top_y = paws_box[1] 
                        p_x = paws_center_x - product_fg.width // 2
                        p_y = paws_top_y - int(product_fg.height * 0.8) 
                    else:
                        self.logger.warning("Could not find paws, falling back to lower center placement.")
                        if subject_fg:
                            m_x_ref = (width - subject_fg.width) // 2
                            m_y_ref = height - subject_fg.height
                            p_x = m_x_ref + (subject_fg.width - product_fg.width) // 2
                            p_y = m_y_ref + int(subject_fg.height * 0.6)
                        else:
                            self.logger.warning("Could not process model image, placing product at image center.")
                            p_x = (width - product_fg.width) // 2
                            p_y = (height - product_fg.height) // 2

                    p_x, p_y = max(0, min(p_x, width-product_fg.width)), max(0, min(p_y, height-product_fg.height))
                    temp_canvas.paste(product_fg, (p_x, p_y), product_fg)
                
                elif not is_for_canny_map and not is_interaction_forced:

            template_id = background_map.get(background_input, "white_default")
            template = self.templates.get(template_id) or self.templates["white_default"]
            self.logger.info(f"Using template: '{template.get('name', template_id)}'")
            params["template_hint"] = template.get("main_prompt_hint")
            params["placement_hint"] = template.get("placement_hint")

            is_image_provided = product_image or model_image
            
            if not is_image_provided:
                self.logger.info("Running in Text-to-Image mode.")
                vae = self.model_manager.load_model("vae", AutoencoderKL, self.config.VAE_PATH)
                pipe = self.model_manager.load_model("pipe_base", StableDiffusionXLPipeline, self.config.SDXL_BASE_MODEL_PATH, vae=vae, use_fp16_variant=True)
                pipe.vae.enable_tiling()
                
                llm_data = build_ad_prompt_compose(pipe.tokenizer_2, inputs, logger=self.logger, openai_api_key=self.config.OPENAI_API_KEY)
                ad_prompt = llm_data["final_prompt_en"]
                base_image_latents = pipe(**encode_prompt_sdxl(pipe, ad_prompt, self.negative_prompt), num_inference_steps=40, generator=generator, width=width, height=height, output_type="latent").images
            
            else:
                self.logger.info("Running in AI Auto-Layout mode.")
                
                background_prompt = template.get("background_prompt")
                vae_bg = self.model_manager.load_model("vae_for_bg", AutoencoderKL, self.config.VAE_PATH)
                bg_pipe = self.model_manager.load_model("pipe_base_for_bg", StableDiffusionXLPipeline, self.config.SDXL_BASE_MODEL_PATH, vae=vae_bg, use_fp16_variant=True)
                background_image = bg_pipe(prompt=background_prompt, num_inference_steps=25, generator=generator, width=width, height=height).images[0]
                output_manager.save(background_image, "00_generated_background")
                
                self.model_manager.unload("pipe_base_for_bg", "vae_for_bg")

                from transformers import CLIPTokenizer
                tokenizer_for_llm = CLIPTokenizer.from_pretrained(self.config.SDXL_BASE_MODEL_PATH, subfolder="tokenizer_2")
                llm_data = build_ad_prompt_compose(tokenizer_for_llm, inputs, logger=self.logger, openai_api_key=self.config.OPENAI_API_KEY)
                ad_prompt = llm_data["final_prompt_en"]
                interaction_detected = llm_data["interaction_detected"]
                del tokenizer_for_llm

                relative_scale = 0.55
                
                condition_image = self._create_composite_ip_image(model_image, product_image, background_image, interaction_detected, relative_scale)
                output_manager.save(condition_image, "00_condition_image_with_bg")
                canny_image = self._prepare_canny_image(condition_image)
                output_manager.save(canny_image, "00_canny_control_image")

                del background_image
                if torch.cuda.is_available(): torch.cuda.empty_cache()

                vae = self.model_manager.load_model("vae_cn", AutoencoderKL, self.config.VAE_PATH)
                controlnet = self.model_manager.load_model("controlnet_canny", ControlNetModel, self.config.CONTROLNET_CANNY_PATH, use_fp16_variant=True)
                pipe = self.model_manager.load_model("pipe_controlnet", StableDiffusionXLControlNetPipeline, self.config.SDXL_BASE_MODEL_PATH, vae=vae, controlnet=controlnet, use_fp16_variant=True)
                
                pipe.load_ip_adapter(self.config.IP_ADAPTER_BASE_PATH, subfolder=os.path.relpath(os.path.dirname(self.config.IP_ADAPTER_WEIGHTS_PATH), self.config.IP_ADAPTER_BASE_PATH), weight_name=os.path.basename(self.config.IP_ADAPTER_WEIGHTS_PATH), image_encoder_folder=self.config.IP_ADAPTER_IMAGE_ENCODER_PATH)
                
                if model_image is None and product_image is not None:
                    self.logger.info("Product only mode detected. Prioritizing style and texture.")
                    controlnet_scale = 0.4
                    ip_adapter_scale = 0.7
                elif interaction_detected:
                    self.logger.info("Interaction detected. Balancing structural control and creative freedom.")
                    controlnet_scale = 0.55 
                    ip_adapter_scale = 0.3
                elif template_id == "white_default" and model_image:
                    self.logger.info("Studio concept hallucination detected. Adjusting scales for 'white_default' template.")
                    ip_adapter_scale = 0.35
                    controlnet_scale = 0.65 
                else:
                    self.logger.info("No special conditions detected. Using template default scales.")
                    controlnet_scale = template.get("controlnet_scale", 0.4)
                    ip_adapter_scale = template.get("ip_adapter_scale", 0.6)

                pipe.set_ip_adapter_scale(ip_adapter_scale)
                self.logger.info(f"[COND] Using scales: ip_scale={ip_adapter_scale}, control_scale={controlnet_scale}")
                
                base_image_latents = pipe(**encode_prompt_sdxl(pipe, ad_prompt, self.negative_prompt), image=canny_image, ip_adapter_image=condition_image, num_inference_steps=40, generator=generator, width=width, height=height, controlnet_conditioning_scale=controlnet_scale, output_type="latent").images

            self.logger.info("Base generation complete. Saving intermediate image and clearing VRAM.")
            if base_image_latents is not None:
                with torch.no_grad():
                    temp_vae = pipe.vae if pipe and hasattr(pipe, 'vae') else self.model_manager.load_model("vae_temp_decode", AutoencoderKL, self.config.VAE_PATH)
                    temp_vae.to(self.config.DEVICE)
                    base_image_latents_scaled = base_image_latents.to(self.config.DEVICE, dtype=temp_vae.dtype) / temp_vae.config.scaling_factor
                    decoded_image_tensor = temp_vae.decode(base_image_latents_scaled, return_dict=False)[0]
                    
                    if pipe and hasattr(pipe, 'image_processor'):
                        image_processor = pipe.image_processor
                    else:
                        temp_pipe = StableDiffusionXLPipeline.from_pretrained(self.config.SDXL_BASE_MODEL_PATH, torch_dtype=self.config.TORCH_DTYPE, use_safetensors=True)
                        image_processor = temp_pipe.image_processor
                        del temp_pipe

                    intermediate_image = image_processor.postprocess(decoded_image_tensor.cpu(), output_type="pil")[0]
                    output_manager.save(intermediate_image, "01_base_generation_output")
                
                base_image_latents = base_image_latents.cpu()

            self.model_manager.unload() 
            if 'pipe' in locals() and pipe is not None: del pipe
            if 'controlnet' in locals() and controlnet is not None: del controlnet
            if 'bg_pipe' in locals() and bg_pipe is not None: del bg_pipe
            if 'condition_image' in locals(): del condition_image
            if 'canny_image' in locals(): del canny_image
            if torch.cuda.is_available(): torch.cuda.empty_cache()

            self.logger.info("Running Refiner pipeline...")
            vae_refiner = self.model_manager.load_model("vae_refiner", AutoencoderKL, self.config.VAE_PATH)
            refiner_pipe = self.model_manager.load_model("pipe_refiner", StableDiffusionXLImg2ImgPipeline, self.config.REFINER_MODEL_PATH, vae=vae_refiner, use_fp16_variant=True)
            refiner_pipe.vae.enable_tiling()
            
            if ad_prompt is None:
                if 'llm_data' in locals() and llm_data and llm_data.get("final_prompt_en"):
                    ad_prompt = llm_data["final_prompt_en"]
                else: 
                    tokenizer = refiner_pipe.tokenizer_2 if hasattr(refiner_pipe, 'tokenizer_2') else None
                    llm_data = build_ad_prompt_compose(tokenizer, inputs, logger=self.logger, openai_api_key=self.config.OPENAI_API_KEY)
                    ad_prompt = llm_data["final_prompt_en"]

            final_image = refiner_pipe(prompt=ad_prompt, negative_prompt=self.negative_prompt, image=base_image_latents.to(self.config.DEVICE), num_inference_steps=40, strength=self.config.REFINER_STRENGTH, generator=generator).images[0]

            if params.get("file_saved", True):
                path = output_manager.save(final_image, f"final_ad_{seed}")
                return {"status": "success", "filepath": path, "seed": seed}
            else:
                return {"status": "success", "image_base64": output_manager.to_base64(final_image), "seed": seed}

        finally:
            self.model_manager.unload()
            if torch.cuda.is_available(): torch.cuda.empty_cache()

    def _load_b64(self, b64_str):
        if not b64_str: return None
        return Image.open(io.BytesIO(base64.b64decode(b64_str))).convert("RGB")

    def _merge_side_by_side(self, left, right, target_height=1024):
        if left.mode != "RGB": left = left.convert("RGB")
        if right.mode != "RGB": right = right.convert("RGB")
        def _resize(img, h):
            w = int(round(img.width * (h/img.height))); return img.resize((w,h), Image.LANCZOS)
        L, R = _resize(left, target_height), _resize(right, target_height)
        merged = Image.new("RGB", (L.width+R.width, target_height)); merged.paste(L, (0,0)); merged.paste(R, (L.width,0))
        return merged