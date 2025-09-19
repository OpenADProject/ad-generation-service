# serve_api.py
import os
import shutil
import subprocess
import tempfile
import base64
import time, uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.requests import Request
from pydantic import BaseModel, field_validator
from PIL import Image
import logging
from logging.handlers import TimedRotatingFileHandler

# 패키지 루트 (…/src/model)
PKG_ROOT = Path(__file__).resolve().parent

# =============================================================================
# Logging (일자별 회전 + 콘솔 동시 출력)
# =============================================================================
# 1) 로그 디렉토리를 PKG_ROOT 기준 절대경로로 고정
LOG_DIR = Path(os.getenv("ADGEN_LOG_DIR", PKG_ROOT / "imagemodel" / "server_log"))
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "adgen.log"

# 2) 핸들러 생성 (파일 회전 + 콘솔)
file_handler = TimedRotatingFileHandler(
    filename=str(LOG_FILE),   
    when="midnight",
    interval=1,
    backupCount=30,
    encoding="utf-8",
    utc=False,
)
stream_handler = logging.StreamHandler()

# 3) 포매터 명시(시간/레벨/로거명)
formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

# 4) 루트 로거 강제 재설정 (uvicorn이 이미 초기화한 경우도 덮어씀)
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, stream_handler],
    force=True,             
)

logger = logging.getLogger("adgen")
logger.info("=== Logging initialized ===")
logger.info(f"Log directory: {LOG_DIR}")

# 5) uvicorn 로거들도 동일 핸들러/레벨로 동기화
for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    lg = logging.getLogger(name)
    lg.handlers = [file_handler, stream_handler]
    lg.setLevel(logging.DEBUG)
    lg.propagate = False

# uvicorn 기본 로거들을 adgen 핸들러로 연결 (파일/콘솔에 동일하게 기록)
uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.handlers = logger.handlers
uvicorn_logger.setLevel(logger.level)
uvicorn_logger.propagate = False

uvicorn_access = logging.getLogger("uvicorn.access")
uvicorn_access.handlers = logger.handlers
uvicorn_access.setLevel(logger.level)
uvicorn_access.propagate = False

uvicorn_error = logging.getLogger("uvicorn.error")
uvicorn_error.handlers = logger.handlers
uvicorn_error.setLevel(logger.level)
uvicorn_error.propagate = False

# =============================================================================
# FastAPI
# =============================================================================
app = FastAPI(title="Ad Gen API", version="1.0.0")

# =============================================================================
# Defaults (env로 덮어쓰기 가능)
# =============================================================================
def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "y")

DEFAULT_SIZE = os.getenv("ADGEN_SIZE", "1080x1080")
DEFAULT_STEPS = int(os.getenv("ADGEN_STEPS", "28"))
DEFAULT_GUIDE = float(os.getenv("ADGEN_GUIDANCE", "7.0"))
DEFAULT_FAMILY = os.getenv("ADGEN_FAMILY", "sdxl")
DEFAULT_VARIANT = os.getenv("ADGEN_VARIANT", "base")
DEFAULT_AUTOMASK = _env_bool("ADGEN_AUTOMASK", True)
DEFAULT_AUTOMASK_METHOD = os.getenv("ADGEN_AUTOMASK_METHOD", "best")
DEFAULT_CPU_OFFLOAD = _env_bool("ADGEN_CPU_OFFLOAD", True)

# =============================================================================
# Utils
# =============================================================================
def _bool_flag(flag: bool, name: str):
    return [f"--{name}"] if flag else []

def _cleanup_dir(path: Path):
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception as e:
        logger.warning("temp cleanup failed: %s", e)

def _build_env(extra: Optional[dict] = None) -> dict:
    """
    subprocess 환경 세팅: PYTHONPATH에 src/model 보장
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PKG_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    if extra:
        env.update({k: str(v) for k, v in extra.items()})
    return env

def _png_path_to_json(path: Path, params: dict) -> dict:
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    try:
        with Image.open(path) as im:
            w, h = im.size
    except Exception:
        w = h = None
    return {
        "ok": True,
        "output": {
            "mime": "image/png",
            "image_b64": b64,
            "width": w,
            "height": h,
        },
        "params": params,
    }

def _stream_png_and_cleanup(path: Path, download_name: Optional[str] = None):
    """
    PNG 스트리밍 후 임시파일/폴더 정리.
    """
    name = download_name or f'bg_replace_{time.strftime("%Y%m%d_%H%M%S")}_{uuid.uuid4().hex[:6]}.png'
    headers = {"Content-Disposition": f'attachment; filename="{name}"'}

    def _iter():
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024 * 64)
                if not chunk:
                    break
                yield chunk
        # 스트림 종료 후 임시 자원 정리
        try:
            tmpdir = path.parent
            path.unlink(missing_ok=True)
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass

    return StreamingResponse(_iter(), media_type="image/png", headers=headers)

def _resolve_input_path(p: str) -> Path:
    """
    입력 경로 해석:
      - 절대경로면 그대로 검증
      - 상대경로면 PKG_ROOT 기준으로 해석 (예: sample/shoes.png → <PKG_ROOT>/sample/shoes.png)
    """
    pp = Path(p)
    if not pp.is_absolute():
        pp = (PKG_ROOT / pp).resolve()
    else:
        pp = pp.resolve()
    return pp

def _resolve_output_path(p: str) -> Path:
    """
    출력 경로 해석:
      - 절대경로면 그대로
      - 상대경로면 PKG_ROOT 기준으로 저장
    """
    pp = Path(p)
    if not pp.is_absolute():
        pp = (PKG_ROOT / pp).resolve()
    else:
        pp = pp.resolve()
    return pp

# =============================================================================
# Health
# =============================================================================
@app.get("/")
def root():
    return {"ok": True, "name": "ad-gen-api", "version": "1.0.0"}

@app.get("/health")
@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.on_event("startup")
async def _startup():
    logger.info("== Startup ==")
    logger.info("CWD(for subprocess)     : %s", PKG_ROOT)
    logger.info("PYTHONPATH              : %s", os.getenv("PYTHONPATH"))
    logger.info("ADSGEN_SDXL_BASE        : %s", os.getenv("ADSGEN_SDXL_BASE"))
    logger.info("HF_HUB_OFFLINE          : %s", os.getenv("HF_HUB_OFFLINE"))
    logger.info("TRANSFORMERS_OFFLINE    : %s", os.getenv("TRANSFORMERS_OFFLINE"))

# =============================================================================
# Pipeline 실행 (bg_replace)
# =============================================================================
def _run_bg_replace_pipeline(
    in_path: Path,
    size: str,
    steps: int,
    guidance: float,
    model_family: str,
    model_variant: str,
    cpu_offload: bool,
    auto_mask: bool,
    auto_mask_method: str,
    prompt: Optional[str] = None,
) -> Path:
    workdir = Path(tempfile.mkdtemp(prefix="adgen-"))
    outdir = workdir / "run"
    outdir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "python", "-m", "model.imagemodel.pipeline",
        "--in", str(in_path),
        "--out", str(outdir),
        "--mode", "bg_replace",
        "--size", size,
        "--steps", str(steps),
        "--guidance", str(guidance),
        "--model_family", model_family,
        "--model_variant", model_variant,
    ]
    cmd += _bool_flag(cpu_offload, "cpu_offload")
    cmd += _bool_flag(auto_mask, "auto_mask")
    if auto_mask:
        cmd += ["--auto_mask_method", auto_mask_method]
    if prompt:
        cmd += ["--prompt", prompt]

    logger.debug("exec cmd: %s", " ".join(cmd))
    logger.debug("exec cwd: %s", PKG_ROOT)

    env = _build_env()
    proc = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        cwd=str(PKG_ROOT),
        env=env,
        timeout=60 * 15,
    )

    if proc.returncode != 0:
        _cleanup_dir(workdir)
        logger.error("Pipeline failed: %s\nstdout=%s\nstderr=%s", " ".join(cmd), proc.stdout, proc.stderr)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "PIPELINE_ERROR",
                "message": "파이프라인 오류",
                "cmd": " ".join(cmd),
                "stdout": proc.stdout[-4000:] if proc.stdout else "",
                "stderr": proc.stderr[-4000:] if proc.stderr else "",
            },
        )

    final_png = outdir / "final.png"
    bg_png = outdir / "bg.png"
    target = final_png if final_png.exists() else bg_png
    if not target or not target.exists():
        _cleanup_dir(workdir)
        logger.error("No result file produced")
        raise HTTPException(
            status_code=500,
            detail={"code": "NO_RESULT", "message": "결과 파일이 없습니다."},
        )

    out_png = Path(tempfile.mkdtemp(prefix="adgen-out-")) / "out.png"
    shutil.copy2(target, out_png)
    _cleanup_dir(workdir)
    logger.info("Pipeline success: %s → %s", in_path, out_png)
    return out_png

# =============================================================================
# 1) multipart/form-data
# =============================================================================
@app.post("/generate/bg_replace")
async def generate_bg_replace(
    file: UploadFile = File(..., description="입력 이미지 (PNG/JPG)"),
    size: str = Form(DEFAULT_SIZE),
    steps: int = Form(DEFAULT_STEPS),
    guidance: float = Form(DEFAULT_GUIDE),
    model_family: str = Form(DEFAULT_FAMILY),
    model_variant: str = Form(DEFAULT_VARIANT),
    auto_mask: bool = Form(DEFAULT_AUTOMASK),
    auto_mask_method: str = Form(DEFAULT_AUTOMASK_METHOD),
    cpu_offload: bool = Form(DEFAULT_CPU_OFFLOAD),
    prompt: Optional[str] = Form(None),
    return_json: bool = Form(False),
    output_path: Optional[str] = Form(None),
):
    tmp_in_dir = Path(tempfile.mkdtemp(prefix="adgen-in-"))
    tmp_in = tmp_in_dir / "input.png"
    try:
        with open(tmp_in, "wb") as f:
            f.write(await file.read())
        out_png = _run_bg_replace_pipeline(
            in_path=tmp_in,
            size=size,
            steps=steps,
            guidance=guidance,
            model_family=model_family,
            model_variant=model_variant,
            cpu_offload=cpu_offload,
            auto_mask=auto_mask,
            auto_mask_method=auto_mask_method,
            prompt=prompt,
        )
    finally:
        shutil.rmtree(tmp_in_dir, ignore_errors=True)

    if output_path:
        out_file = _resolve_output_path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out_png, out_file)
        logger.info("Saved output to %s", out_file)
        return {"ok": True, "output_path": str(out_file)}

    if return_json:
        params = dict(
            size=size, steps=steps, guidance=guidance,
            model_family=model_family, model_variant=model_variant,
            cpu_offload=cpu_offload, auto_mask=auto_mask,
            auto_mask_method=auto_mask_method, prompt=prompt,
        )
        payload = _png_path_to_json(out_png, params)
        # JSON 응답이면 임시결과 정리
        try:
            out_dir = out_png.parent
            out_png.unlink(missing_ok=True)
            shutil.rmtree(out_dir, ignore_errors=True)
        except Exception:
            pass
        return JSONResponse(payload)

    # 파일 스트리밍 응답 (다운로드 이름 자동)
    return _stream_png_and_cleanup(out_png)

# =============================================================================
# 2) application/json
# =============================================================================
class BgReplaceJSON(BaseModel):
    image_b64: Optional[str] = None
    image_path: Optional[str] = None
    prompt: Optional[str] = None

    size: str = DEFAULT_SIZE
    steps: int = DEFAULT_STEPS
    guidance: float = DEFAULT_GUIDE
    model_family: str = DEFAULT_FAMILY
    model_variant: str = DEFAULT_VARIANT
    cpu_offload: bool = DEFAULT_CPU_OFFLOAD
    auto_mask: bool = DEFAULT_AUTOMASK
    auto_mask_method: str = DEFAULT_AUTOMASK_METHOD

    # 응답 형태
    return_json: bool = True
    output_path: Optional[str] = None

    @field_validator("auto_mask_method")
    @classmethod
    def _check_method(cls, v: str):
        allowed = {"best", "rembg", "sam"}
        if v not in allowed:
            raise ValueError("auto_mask_method must be one of best, rembg, sam")
        return v

@app.post("/generate/bg_replace_json")
async def generate_bg_replace_json(payload: BgReplaceJSON):
    logger.info("New JSON request received")
    logger.debug("Payload: %s", payload.model_dump())

    tmp_in_dir = Path(tempfile.mkdtemp(prefix="adgen-in-"))
    tmp_in = tmp_in_dir / "input.png"

    try:
        # 1) 입력 이미지 확보
        if payload.image_b64:
            logger.debug("Decoding base64 image")
            try:
                img_bytes = base64.b64decode(payload.image_b64, validate=True)
            except Exception:
                logger.error("Failed to decode base64 image")
                raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "image_b64 디코딩 실패"})
            with open(tmp_in, "wb") as f:
                f.write(img_bytes)
            logger.info("Base64 image saved to %s", tmp_in)
        else:
            p = _resolve_input_path(payload.image_path)
            logger.info("Resolved input path: %s", p)
            try:
                exists = p.exists()   # <-- 여기서 PermissionError 날 수 있음
            except PermissionError:
                logger.exception("Permission error while checking input path")
                raise HTTPException(
                    status_code=403,
                    detail={
                        "code": "FS_PERMISSION",
                        "message": f"서버 프로세스가 파일을 읽을 권한이 없습니다: {p} "
                                   f"(공유 디렉터리 사용 또는 권한 조정 필요)"
                    }
                )
            if not exists:
                logger.error("Input image not found: %s", p)
                raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": f"image_path 없음: {p}"})

            # 열람 권한이 실제로 있는지도 한번 더 확인 (open 시점 PermissionError 대응)
            try:
                with open(p, "rb") as src, open(tmp_in, "wb") as dst:
                    shutil.copyfileobj(src, dst)
            except PermissionError:
                logger.exception("Permission error while opening input file")
                raise HTTPException(
                    status_code=403,
                    detail={"code": "FS_PERMISSION", "message": f"파일 열기 권한이 없습니다: {p}"}
                )
            logger.info("Copied input image to %s", tmp_in)

        # 2) 파이프라인 실행
        out_png = _run_bg_replace_pipeline(
            in_path=tmp_in,
            size=payload.size,
            steps=payload.steps,
            guidance=payload.guidance,
            model_family=payload.model_family,
            model_variant=payload.model_variant,
            cpu_offload=payload.cpu_offload,
            auto_mask=payload.auto_mask,
            auto_mask_method=payload.auto_mask_method,
            prompt=payload.prompt,
        )
        logger.info("Pipeline finished successfully. Output: %s", out_png)

    except HTTPException:
        # 이미 의미있는 상태코드/메시지로 구성됨
        logger.exception("Handled HTTPException in bg_replace_json")
        raise
    except Exception:
        logger.exception("Unhandled exception during bg_replace_json")
        raise
    finally:
        shutil.rmtree(tmp_in_dir, ignore_errors=True)

    # 3) 결과 처리
    if payload.output_path:
        out_file = _resolve_output_path(payload.output_path)
        try:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(out_png, out_file)
        except PermissionError:
            logger.exception("Permission error while writing output_path")
            raise HTTPException(
                status_code=403,
                detail={"code":"FS_PERMISSION","message":f"output_path 권한 없음: {out_file}"}
            )
        logger.info("Saved output to %s", out_file)
        return {"ok": True, "output_path": str(out_file)}

    if payload.return_json:
        params = dict(
            size=payload.size, steps=payload.steps, guidance=payload.guidance,
            model_family=payload.model_family, model_variant=payload.model_variant,
            cpu_offload=payload.cpu_offload, auto_mask=payload.auto_mask,
            auto_mask_method=payload.auto_mask_method, prompt=payload.prompt,
        )
        payload_json = _png_path_to_json(out_png, params)
        logger.info("Returning JSON response with embedded image")
        # 임시결과 정리
        try:
            out_dir = out_png.parent
            out_png.unlink(missing_ok=True)
            shutil.rmtree(out_dir, ignore_errors=True)
        except Exception:
            logger.warning("Failed to cleanup temporary output dir")
        return JSONResponse(payload_json)

    logger.info("Returning FileResponse for download")
    return FileResponse(
        path=out_png,
        media_type="image/png",
        filename=f"bgreplace_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.png",
    )

@app.exception_handler(HTTPException)
async def _http_exc_handler(request: Request, exc: HTTPException):
    logger.error("HTTPException %s on %s %s: %s", exc.status_code, request.method, request.url.path, exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(Exception)
async def _unhandled_exc_handler(request: Request, exc: Exception):
    logger.exception("UNHANDLED Exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail":{"code":"UNHANDLED","message":str(exc)}})