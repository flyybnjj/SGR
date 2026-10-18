
import re


def rgb(color):
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def hex_color(values):
    return "#" + "".join(f"{round(v):02x}" for v in values)


def luminance(color):
    channels = [v / 255 for v in rgb(color)]
    return sum((v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4) * w
               for v, w in zip(channels, (.2126, .7152, .0722)))


def contrast(first, second):
    low, high = sorted((luminance(first), luminance(second)))
    return (high + .05) / (low + .05)


def theme_tokens(color):
    color = color.lower() if isinstance(color, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", color) else "#b80003"
    tint = hex_color(v * .10 + 255 * .90 for v in rgb(color))
    ink = color
    while min(contrast(ink, tint), contrast(ink, "#f5f5f7")) < 4.5:
        ink = hex_color(v * .9 for v in rgb(ink))
    foreground = max(("#ffffff", "#17212f"), key=lambda candidate: contrast(color, candidate))

    if contrast(color, foreground) < 4.5:
        foreground = "#000000"
    return {"color": color, "on_color": foreground, "ink": ink,
            "tint": tint, "hover": hex_color(v * .85 for v in rgb(color))}


def theme_style(color):
    tokens = theme_tokens(color)
    return ";".join(f"--{name}: {value}" if name == "delegation-color" else f"--{name}:{value}" for name, value in {
        "delegation-color": color if isinstance(color, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", color) else tokens["color"], "muni-red-primary": tokens["color"],
        "muni-red": tokens["ink"], "accent-on": tokens["on_color"],
        "accent-hover": tokens["hover"], "muni-red-tint": tokens["tint"],
        "muni-red-tint-strong": tokens["tint"], "muni-red-border": tokens["ink"],
        "border-stitch-focus": tokens["ink"],
    }.items())
