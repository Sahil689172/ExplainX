"""Request validation for the Image Generation Engine."""

from __future__ import annotations

from image_generation.config import ImageGenerationConfig
from image_generation.exceptions import ValidationError
from image_generation.models import GenerationMode, GenerationRequest, OutputFormat


class GenerationRequestValidator:
    """Validates prompt, style, resolution, aspect ratio, format, and mode."""

    def __init__(self, config: ImageGenerationConfig) -> None:
        self._config = config

    def validate(self, request: GenerationRequest) -> None:
        errors: list[ValidationError] = []

        prompt = (request.prompt or "").strip()
        if not prompt:
            errors.append(ValidationError("Prompt must not be empty", field="prompt"))
        elif len(prompt) > 4000:
            errors.append(
                ValidationError("Prompt exceeds 4000 characters", field="prompt")
            )

        style = (request.style_id or "").strip()
        if not style:
            errors.append(ValidationError("style_id is required", field="style_id"))
        elif not self._config.is_style_supported(style):
            errors.append(
                ValidationError(
                    f"Unsupported style_id {style!r}; "
                    f"allowed={list(self._config.supported_styles)}",
                    field="style_id",
                )
            )

        if request.width <= 0 or request.height <= 0:
            errors.append(
                ValidationError(
                    "width and height must be positive", field="resolution"
                )
            )
        elif not self._config.is_resolution_supported(request.width, request.height):
            errors.append(
                ValidationError(
                    f"Unsupported resolution {request.width}x{request.height}; "
                    f"allowed={list(self._config.supported_resolutions)}",
                    field="resolution",
                )
            )

        ratio = (request.aspect_ratio or "").strip()
        if ratio not in self._config.supported_aspect_ratios:
            errors.append(
                ValidationError(
                    f"Unsupported aspect_ratio {ratio!r}; "
                    f"allowed={list(self._config.supported_aspect_ratios)}",
                    field="aspect_ratio",
                )
            )

        fmt = request.output_format
        if not isinstance(fmt, OutputFormat):
            errors.append(
                ValidationError(
                    f"Invalid output_format {fmt!r}", field="output_format"
                )
            )
        elif fmt.value not in self._config.supported_output_formats:
            errors.append(
                ValidationError(
                    f"Unsupported output_format {fmt.value!r}",
                    field="output_format",
                )
            )

        if not isinstance(request.mode, GenerationMode):
            errors.append(
                ValidationError(f"Invalid generation mode {request.mode!r}", field="mode")
            )

        if errors:
            # Raise first with combined message for callers that catch once
            messages = "; ".join(str(e) for e in errors)
            raise ValidationError(messages, field=errors[0].field)
