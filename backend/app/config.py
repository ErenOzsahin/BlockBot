from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    debug_overlays: bool = False
    max_upload_bytes: int = 5 * 1024 * 1024

    # Vision thresholds (tune per theme / device)
    canny_low: int = 50
    canny_high: int = 150
    min_contour_area: int = 10000
    cell_brightness_threshold: int = 100
    piece_brightness_threshold: int = 70
    piece_region_top_ratio: float = 0.58
    piece_slot_count: int = 3


settings = Settings()
