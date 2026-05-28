from __future__ import annotations

import math
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "diagrams"

COLORS = {
    "ink": "#111827",
    "muted": "#4B5563",
    "line": "#111827",
    "blue": "#374151",
    "light_blue": "#E5E7EB",
    "pale_blue": "#F9FAFB",
    "green": "#E8F5E9",
    "gold": "#FFF7D6",
    "red": "#FDE8E8",
    "gray": "#F3F4F6",
    "white": "#FFFFFF",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size, index=1 if bold else 0)
        except Exception:
            pass
    return ImageFont.load_default()


TITLE = font(38, True)
SUBTITLE = font(25, True)
BODY = font(22)
BODY_BOLD = font(22, True)
SMALL = font(18)
SMALL_BOLD = font(18, True)
TINY = font(15)


class Diagram:
    def __init__(self, title: str, width: int = 1800, height: int = 1100):
        self.image = Image.new("RGB", (width, height), COLORS["white"])
        self.draw = ImageDraw.Draw(self.image)
        self.width = width
        self.height = height
        self.draw.rectangle((0, 0, width - 1, height - 1), outline="#CBD5E1", width=2)
        self.text((60, 34, width - 60, 90), title, TITLE, COLORS["ink"], align="center")
        self.draw.line((70, 105, width - 70, 105), fill="#CBD5E1", width=3)

    def save(self, filename: str) -> None:
        OUT.mkdir(parents=True, exist_ok=True)
        self.image.save(OUT / filename, quality=95)

    def text(self, box, text: str, fnt, fill=COLORS["ink"], align="center", spacing=5):
        x1, y1, x2, y2 = box
        max_width = x2 - x1 - 16
        words = text.split()
        lines: list[str] = []
        line = ""
        for word in words:
            test = f"{line} {word}".strip()
            if self.draw.textbbox((0, 0), test, font=fnt)[2] <= max_width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        if not lines:
            lines = [""]
        heights = [self.draw.textbbox((0, 0), ln, font=fnt)[3] for ln in lines]
        total = sum(heights) + spacing * (len(lines) - 1)
        y = y1 + ((y2 - y1 - total) / 2)
        for ln, h in zip(lines, heights):
            bbox = self.draw.textbbox((0, 0), ln, font=fnt)
            w = bbox[2] - bbox[0]
            if align == "left":
                x = x1 + 10
            elif align == "right":
                x = x2 - w - 10
            else:
                x = x1 + ((x2 - x1 - w) / 2)
            self.draw.text((x, y), ln, font=fnt, fill=fill)
            y += h + spacing

    def box(self, xy, text: str, fill=COLORS["pale_blue"], outline=COLORS["blue"], radius=18, fnt=BODY_BOLD):
        self.draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=3)
        self.text(xy, text, fnt)

    def rect(self, xy, text: str, fill=COLORS["white"], outline=COLORS["line"], fnt=BODY_BOLD):
        self.draw.rectangle(xy, fill=fill, outline=outline, width=3)
        self.text(xy, text, fnt)

    def ellipse(self, xy, text: str, fill=COLORS["white"], outline=COLORS["blue"], fnt=BODY):
        self.draw.ellipse(xy, fill=fill, outline=outline, width=3)
        self.text(xy, text, fnt)

    def diamond(self, cx: int, cy: int, w: int, h: int, text: str):
        pts = [(cx, cy - h // 2), (cx + w // 2, cy), (cx, cy + h // 2), (cx - w // 2, cy)]
        self.draw.polygon(pts, fill=COLORS["gold"], outline=COLORS["line"])
        self.draw.line(pts + [pts[0]], fill=COLORS["line"], width=3)
        self.text((cx - w // 2 + 10, cy - h // 2 + 10, cx + w // 2 - 10, cy + h // 2 - 10), text, BODY_BOLD)

    def arrow(self, start, end, fill=COLORS["line"], width=3, label: str | None = None, dashed=False):
        x1, y1 = start
        x2, y2 = end
        if dashed:
            self.dashed_line(start, end, fill, width)
        else:
            self.draw.line((x1, y1, x2, y2), fill=fill, width=width)
        angle = math.atan2(y2 - y1, x2 - x1)
        length = 18
        spread = math.pi / 7
        p1 = (x2 - length * math.cos(angle - spread), y2 - length * math.sin(angle - spread))
        p2 = (x2 - length * math.cos(angle + spread), y2 - length * math.sin(angle + spread))
        self.draw.polygon([(x2, y2), p1, p2], fill=fill)
        if label:
            mx = (x1 + x2) / 2
            my = (y1 + y2) / 2
            bbox = self.draw.textbbox((0, 0), label, font=TINY)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            self.draw.rounded_rectangle((mx - tw / 2 - 6, my - th / 2 - 5, mx + tw / 2 + 6, my + th / 2 + 5), 8, fill=COLORS["white"])
            self.draw.text((mx - tw / 2, my - th / 2 - 1), label, font=TINY, fill=COLORS["muted"])

    def dashed_line(self, start, end, fill=COLORS["line"], width=2, dash=12, gap=8):
        x1, y1 = start
        x2, y2 = end
        dx, dy = x2 - x1, y2 - y1
        distance = math.hypot(dx, dy)
        steps = int(distance // (dash + gap)) + 1
        for i in range(steps):
            a = i * (dash + gap) / distance
            b = min((i * (dash + gap) + dash) / distance, 1)
            self.draw.line((x1 + dx * a, y1 + dy * a, x1 + dx * b, y1 + dy * b), fill=fill, width=width)

    def orthogonal_arrow(self, points, fill=COLORS["line"], width=3, label: str | None = None):
        for start, end in zip(points, points[1:]):
            self.draw.line((*start, *end), fill=fill, width=width)
        if len(points) >= 2:
            self.arrow(points[-2], points[-1], fill=fill, width=width, label=label)

    def actor(self, cx: int, cy: int, label: str):
        self.draw.ellipse((cx - 25, cy - 70, cx + 25, cy - 20), outline=COLORS["line"], width=4)
        self.draw.line((cx, cy - 20, cx, cy + 60), fill=COLORS["line"], width=4)
        self.draw.line((cx - 55, cy + 5, cx + 55, cy + 5), fill=COLORS["line"], width=4)
        self.draw.line((cx, cy + 60, cx - 45, cy + 125), fill=COLORS["line"], width=4)
        self.draw.line((cx, cy + 60, cx + 45, cy + 125), fill=COLORS["line"], width=4)
        self.text((cx - 115, cy + 138, cx + 115, cy + 210), label, BODY_BOLD)

    def class_box(self, xy, title: str, attrs: list[str], methods: list[str] | None = None):
        x1, y1, x2, y2 = xy
        self.draw.rectangle(xy, fill=COLORS["white"], outline=COLORS["line"], width=3)
        self.draw.rectangle((x1, y1, x2, y1 + 48), fill=COLORS["light_blue"], outline=COLORS["line"], width=3)
        self.text((x1, y1, x2, y1 + 48), title, BODY_BOLD)
        y = y1 + 62
        for attr in attrs:
            self.draw.text((x1 + 14, y), attr, font=TINY, fill=COLORS["ink"])
            y += 25
        if methods:
            self.draw.line((x1, y + 4, x2, y + 4), fill=COLORS["line"], width=2)
            y += 16
            for method in methods:
                self.draw.text((x1 + 14, y), method, font=TINY, fill=COLORS["ink"])
                y += 25

    def table_entity(self, xy, title: str, fields: list[str]):
        x1, y1, x2, y2 = xy
        self.draw.rectangle(xy, fill=COLORS["white"], outline=COLORS["line"], width=3)
        self.draw.rectangle((x1, y1, x2, y1 + 50), fill=COLORS["light_blue"], outline=COLORS["line"], width=3)
        self.text((x1, y1, x2, y1 + 50), title, BODY_BOLD)
        y = y1 + 64
        for field in fields:
            self.draw.text((x1 + 12, y), field, font=TINY, fill=COLORS["ink"])
            y += 25

    def note(self, xy, text: str, side: str = "left"):
        x1, y1, x2, y2 = xy
        if side == "left":
            pts = [(x2, y1), (x1, y1), (x1, y2), (x2, y2)]
            self.draw.line(pts, fill=COLORS["line"], width=3)
        else:
            pts = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
            self.draw.line(pts, fill=COLORS["line"], width=3)
        self.text((x1 + 8, y1 + 8, x2 - 8, y2 - 8), text, TINY, fill=COLORS["ink"], align="left", spacing=3)

    def event_circle(self, cx: int, cy: int, r: int = 24, fill=COLORS["white"]):
        self.draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=COLORS["line"], fill=fill, width=3)

    def gateway(self, cx: int, cy: int, size: int = 72):
        half = size // 2
        pts = [(cx, cy - half), (cx + half, cy), (cx, cy + half), (cx - half, cy)]
        self.draw.polygon(pts, fill=COLORS["white"], outline=COLORS["line"])
        self.draw.line(pts + [pts[0]], fill=COLORS["line"], width=3)
        self.draw.line((cx - 14, cy - 14, cx + 14, cy + 14), fill=COLORS["line"], width=4)
        self.draw.line((cx + 14, cy - 14, cx - 14, cy + 14), fill=COLORS["line"], width=4)


def use_case() -> None:
    d = Diagram("Use Case Diagram", 1800, 1100)
    d.actor(180, 525, "Primary User")
    d.actor(1620, 525, "Tester / Evaluator")
    d.draw.rounded_rectangle((430, 145, 1370, 1000), 26, outline=COLORS["blue"], width=4, fill="#FBFDFF")
    d.text((470, 165, 1330, 215), "Multimodal Video Understanding Engine", SUBTITLE)
    ovals = {
        "upload": (690, 255, 1110, 345, "Upload Video"),
        "analyze": (690, 400, 1110, 490, "Analyze Video"),
        "timeline": (690, 545, 1110, 635, "View Timeline"),
        "ask": (690, 690, 1110, 780, "Ask Question About Video"),
        "evidence": (690, 835, 1110, 925, "View Timestamped Evidence"),
    }
    for xy in ovals.values():
        d.ellipse(xy[:4], xy[4])
    left_points = [(690, 300), (690, 445), (690, 590), (690, 735), (690, 880)]
    right_points = [(1110, 300), (1110, 445), (1110, 590), (1110, 735)]
    for end in left_points:
        d.draw.line((265, 555, *end), fill=COLORS["line"], width=3)
    for end in right_points:
        d.draw.line((1535, 555, *end), fill=COLORS["line"], width=3)
    d.save("use_case_diagram.png")


def context() -> None:
    d = Diagram("System Context Diagram", 2000, 1120)
    d.box((740, 330, 1260, 860), "Multimodal Video\nUnderstanding Engine", COLORS["light_blue"], fnt=SUBTITLE)

    d.box((120, 300, 450, 440), "User", COLORS["white"])
    d.box((120, 585, 450, 735), "Swagger UI /\nFuture Web UI", COLORS["white"])
    d.box((1510, 235, 1880, 385), "OpenAI APIs", COLORS["white"])
    d.box((1510, 475, 1880, 625), "FFmpeg / OpenCV /\nPySceneDetect", COLORS["white"])
    d.box((1510, 715, 1880, 865), "Local Files\nand SQLite", COLORS["white"])

    d.arrow((450, 350), (740, 350), label="upload video, ask question")
    d.arrow((740, 405), (450, 405), label="status, timeline, answer")

    d.arrow((450, 635), (740, 635), label="HTTP REST")
    d.arrow((740, 690), (450, 690), label="JSON responses")

    d.orthogonal_arrow([(1260, 405), (1380, 405), (1380, 310), (1510, 310)], label="audio, frames, prompts")
    d.orthogonal_arrow([(1510, 360), (1420, 360), (1420, 460), (1260, 460)], label="transcript, summaries")

    d.arrow((1260, 535), (1510, 535), label="processing commands")
    d.arrow((1510, 590), (1260, 590), label="audio, frames, scenes")

    d.arrow((1260, 760), (1510, 760), label="write video memory")
    d.arrow((1510, 815), (1260, 815), label="read evidence")
    d.save("system_context_diagram.png")


def dfd() -> None:
    d = Diagram("Level-1 Data Flow Diagram", 2200, 1300)
    d.actor(130, 555, "User")
    processes = [
        ((390, 190, 690, 300), "1. Upload\nVideo"),
        ((830, 190, 1130, 300), "2. Extract\nAudio"),
        ((1265, 190, 1585, 300), "3. Transcribe\nAudio"),
        ((830, 600, 1130, 710), "4. Extract\nKeyframes"),
        ((1265, 600, 1585, 710), "5. Detect\nScenes"),
        ((1700, 385, 2050, 510), "6. Build\nTimeline"),
        ((1700, 850, 2050, 970), "7. Ask Video\nQuestion"),
    ]
    for xy, label in processes:
        d.box(xy, label, COLORS["pale_blue"])
    stores = [
        ((390, 420, 690, 500), "D1 Raw Video Files"),
        ((390, 640, 690, 720), "D2 Video Metadata"),
        ((830, 420, 1130, 500), "D3 Audio Files"),
        ((1265, 420, 1585, 500), "D4 Transcript Segments"),
        ((830, 820, 1130, 900), "D5 Keyframe Images"),
        ((1265, 820, 1585, 900), "D6 Scene Records"),
        ((1700, 640, 2050, 720), "D7 Timeline Events"),
    ]
    for xy, label in stores:
        d.rect(xy, label, COLORS["gray"])
    d.orthogonal_arrow([(230, 585), (300, 585), (300, 245), (390, 245)], label="video")
    d.arrow((540, 300), (540, 420), label="raw file")
    d.orthogonal_arrow([(690, 245), (745, 245), (745, 680), (690, 680)], label="metadata")

    d.orthogonal_arrow([(690, 460), (765, 460), (765, 245), (830, 245)], label="raw video")
    d.arrow((980, 300), (980, 420), label="audio")
    d.orthogonal_arrow([(1130, 460), (1200, 460), (1200, 245), (1265, 245)], label="audio")
    d.arrow((1425, 300), (1425, 420), label="segments")
    d.orthogonal_arrow([(1585, 460), (1650, 460), (1650, 445), (1700, 445)])

    d.orthogonal_arrow([(690, 460), (765, 460), (765, 655), (830, 655)], label="raw video")
    d.arrow((980, 710), (980, 820), label="frames")
    d.orthogonal_arrow([(980, 820), (980, 760), (1640, 760), (1640, 470), (1700, 470)])

    d.orthogonal_arrow([(690, 460), (765, 460), (765, 555), (1220, 555), (1220, 655), (1265, 655)], label="raw video")
    d.arrow((1425, 710), (1425, 820), label="scenes")
    d.orthogonal_arrow([(1585, 860), (1665, 860), (1665, 495), (1700, 495)])

    d.arrow((1875, 510), (1875, 640), label="timeline")
    d.arrow((1875, 720), (1875, 850), label="video memory")
    d.orthogonal_arrow([(230, 635), (270, 635), (270, 1120), (1790, 1120), (1790, 970)], label="question")
    d.orthogonal_arrow([(1700, 910), (1540, 910), (1540, 1040), (230, 1040), (230, 690)], label="answer")
    d.save("level_1_dfd.png")


def pipeline() -> None:
    d = Diagram("Processing Pipeline Diagram", 2200, 1200)
    steps = [
        (120, 190, "Uploaded\nVideo"),
        (390, 190, "Validate\nFile"),
        (660, 190, "Store\nVideo"),
        (1000, 150, "Extract\nAudio"),
        (1300, 150, "Transcribe\nAudio"),
        (1000, 440, "Sample\nKeyframes"),
        (1300, 440, "Analyze Selected\nFrames"),
        (1000, 730, "Detect\nScenes"),
        (1640, 440, "Build\nTimeline"),
        (1880, 440, "Store Video\nMemory"),
        (1880, 750, "Answer User\nQuestions"),
    ]
    boxes = []
    for x, y, label in steps:
        xy = (x, y, x + 210, y + 105)
        d.box(xy, label, COLORS["pale_blue"])
        boxes.append(xy)

    def mid_right(xy):
        return (xy[2], (xy[1] + xy[3]) // 2)

    def mid_left(xy):
        return (xy[0], (xy[1] + xy[3]) // 2)

    def mid_bottom(xy):
        return ((xy[0] + xy[2]) // 2, xy[3])

    def mid_top(xy):
        return ((xy[0] + xy[2]) // 2, xy[1])

    for a, b in [(0, 1), (1, 2), (3, 4), (5, 6), (8, 9)]:
        d.arrow(mid_right(boxes[a]), mid_left(boxes[b]))

    store = boxes[2]
    d.orthogonal_arrow([mid_right(store), (930, 242), (930, 202), mid_left(boxes[3])], label="audio path")
    d.orthogonal_arrow([mid_bottom(store), (765, 492), mid_left(boxes[5])], label="visual path")
    d.orthogonal_arrow([mid_bottom(store), (765, 782), mid_left(boxes[7])], label="scene path")
    d.orthogonal_arrow([mid_right(boxes[4]), (1585, 202), (1585, 492), mid_left(boxes[8])])
    d.arrow(mid_right(boxes[6]), mid_left(boxes[8]))
    d.orthogonal_arrow([mid_right(boxes[7]), (1585, 782), (1585, 545), (1640, 545)])
    d.arrow(mid_bottom(boxes[9]), mid_top(boxes[10]))
    d.save("processing_pipeline_diagram.png")


def activity() -> None:
    d = Diagram("Activity Diagram", 2200, 1250)
    steps = [
        ((120, 235, 390, 315), "Start", COLORS["green"]),
        ((510, 235, 830, 315), "Upload video", COLORS["pale_blue"]),
        ((960, 215, 1240, 335), "File valid?", COLORS["gold"]),
        ((1370, 235, 1690, 315), "Store video\nrecord", COLORS["pale_blue"]),
        ((1810, 235, 2110, 315), "Request\nanalysis", COLORS["pale_blue"]),
        ((1810, 500, 2110, 580), "Extract audio,\nframes, scenes", COLORS["pale_blue"]),
        ((1370, 500, 1690, 580), "Transcribe and\nanalyze frames", COLORS["pale_blue"]),
        ((960, 500, 1240, 580), "Build and save\ntimeline", COLORS["pale_blue"]),
        ((510, 480, 830, 600), "User asks\nquestion?", COLORS["gold"]),
        ((120, 415, 390, 495), "Return\ntimeline", COLORS["green"]),
        ((120, 665, 390, 745), "Retrieve evidence\nand answer", COLORS["green"]),
        ((510, 665, 830, 745), "Return answer\nwith timestamps", COLORS["green"]),
        ((960, 760, 1240, 840), "End", COLORS["green"]),
        ((1370, 380, 1690, 460), "Return validation\nerror", COLORS["red"]),
    ]
    for xy, label, fill in steps:
        if "?" in label:
            x1, y1, x2, y2 = xy
            d.diamond((x1 + x2) // 2, (y1 + y2) // 2, x2 - x1, y2 - y1, label)
        elif label in {"Start", "End"}:
            d.ellipse(xy, label, fill)
        else:
            d.box(xy, label, fill, fnt=SMALL_BOLD)
    d.arrow((390, 275), (510, 275))
    d.arrow((830, 275), (960, 275))
    d.arrow((1240, 275), (1370, 275), label="Yes")
    d.arrow((1240, 275), (1370, 420), label="No")
    d.arrow((1690, 275), (1810, 275))
    d.arrow((1960, 315), (1960, 500))
    d.arrow((1810, 540), (1690, 540))
    d.arrow((1370, 540), (1240, 540))
    d.arrow((960, 540), (830, 540))
    d.arrow((510, 540), (390, 455), label="No")
    d.arrow((670, 600), (390, 705), label="Yes")
    d.arrow((390, 705), (510, 705))
    d.arrow((830, 705), (1020, 780))
    d.save("activity_diagram.png")


def sequence_upload() -> None:
    d = Diagram("Upload and Analysis Sequence Diagram", 2000, 1280)
    participants = [
        ("User", 150),
        ("FastAPI API", 430),
        ("Video Processor", 740),
        ("Media Services", 1060),
        ("AI Services", 1380),
        ("SQLite DB", 1710),
    ]
    for name, x in participants:
        d.box((x - 105, 150, x + 105, 220), name, COLORS["light_blue"], fnt=SMALL_BOLD)
        d.dashed_line((x, 220), (x, 1160), "#94A3B8", 2)
    msgs = [
        (150, 430, 275, "POST /videos/upload"),
        (430, 1710, 345, "create video record"),
        (1710, 430, 415, "video_id"),
        (430, 150, 485, "status = uploaded"),
        (150, 430, 590, "POST /videos/{id}/analyze"),
        (430, 740, 660, "analyze(video_id)"),
        (740, 1710, 730, "status = processing"),
        (740, 1060, 800, "extract audio"),
        (740, 1060, 870, "extract keyframes"),
        (740, 1060, 940, "detect scenes"),
        (740, 1380, 1010, "transcribe audio"),
        (740, 1380, 1080, "analyze selected frames"),
        (740, 1710, 1150, "save timeline + analyzed"),
        (740, 430, 1210, "analysis summary"),
    ]
    for x1, x2, y, label in msgs:
        d.arrow((x1, y), (x2, y), label=label, dashed=x2 < x1)
    d.save("upload_analysis_sequence.png")


def sequence_ask() -> None:
    d = Diagram("Ask Video Sequence Diagram", 1900, 1120)
    participants = [("User", 160), ("FastAPI API", 430), ("Question Answerer", 740), ("Evidence Retriever", 1070), ("SQLite DB", 1380), ("Language Model", 1640)]
    for name, x in participants:
        d.box((x - 100, 150, x + 100, 220), name, COLORS["light_blue"], fnt=SMALL_BOLD)
        d.dashed_line((x, 220), (x, 1010), "#94A3B8", 2)
    msgs = [
        (160, 430, 300, "POST /videos/{id}/ask"),
        (430, 1380, 370, "load video status"),
        (1380, 430, 440, "analyzed"),
        (430, 740, 510, "answer(video_id, question)"),
        (740, 1070, 580, "find relevant evidence"),
        (1070, 1380, 650, "query video memory"),
        (1380, 1070, 720, "timeline + transcript + frames"),
        (1070, 740, 790, "compact evidence package"),
        (740, 1640, 860, "generate answer"),
        (1640, 740, 930, "answer text"),
        (740, 430, 1000, "answer + evidence"),
        (430, 160, 1060, "response with timestamps"),
    ]
    for x1, x2, y, label in msgs:
        d.arrow((x1, y), (x2, y), label=label, dashed=x2 < x1)
    d.save("ask_video_sequence.png")


def class_diagram() -> None:
    d = Diagram("Domain Class Diagram", 2200, 1450)
    d.class_box((895, 150, 1305, 485), "Video", ["+ id: string", "+ originalFilename: string", "+ storedPath: string", "+ status: string", "+ createdAt: datetime", "+ updatedAt: datetime", "+ errorMessage: string"], ["+ markProcessing()", "+ markAnalyzed()", "+ markFailed()"])
    classes = [
        ((80, 720, 465, 960), "TranscriptSegment", ["+ id: string", "+ videoId: string", "+ startTime: float", "+ endTime: float", "+ text: string"]),
        ((600, 720, 985, 960), "Keyframe", ["+ id: string", "+ videoId: string", "+ time: float", "+ path: string", "+ visualSummary: string"]),
        ((1120, 720, 1505, 960), "Scene", ["+ id: string", "+ videoId: string", "+ startTime: float", "+ endTime: float", "+ summary: string"]),
        ((1640, 720, 2025, 980), "TimelineEvent", ["+ id: string", "+ videoId: string", "+ startTime: float", "+ endTime: float", "+ summary: string"]),
        ((1640, 1080, 2025, 1300), "EvidenceLink", ["+ id: string", "+ timelineEventId: string", "+ evidenceType: string", "+ evidenceId: string"]),
    ]
    for xy, title, attrs in classes:
        d.class_box(xy, title, attrs)
    root = (1100, 485)
    for end in [(272, 720), (792, 720), (1312, 720), (1832, 720)]:
        d.arrow(root, end, label="1 to many")
    d.arrow((1832, 980), (1832, 1080), label="1 to many")
    d.save("domain_class_diagram.png")


def erd() -> None:
    d = Diagram("Entity Relationship Diagram", 2200, 1350)
    d.table_entity((895, 150, 1305, 500), "VIDEO", ["PK id", "original_filename", "stored_path", "status", "created_at", "updated_at", "error_message"])
    entities = [
        ((110, 700, 495, 950), "TRANSCRIPT_SEGMENT", ["PK id", "FK video_id", "start_time", "end_time", "text"]),
        ((610, 700, 995, 950), "KEYFRAME", ["PK id", "FK video_id", "time", "path", "visual_summary"]),
        ((1110, 700, 1495, 950), "SCENE", ["PK id", "FK video_id", "start_time", "end_time", "summary"]),
        ((1610, 700, 1995, 970), "TIMELINE_EVENT", ["PK id", "FK video_id", "start_time", "end_time", "summary"]),
        ((1610, 1050, 1995, 1275), "EVIDENCE_LINK", ["PK id", "FK timeline_event_id", "evidence_type", "evidence_id"]),
    ]
    for xy, title, fields in entities:
        d.table_entity(xy, title, fields)
    root = (1100, 500)
    children = [
        (302, 700),
        (802, 700),
        (1302, 700),
        (1802, 700),
    ]
    for end in children:
        d.arrow(root, end, label="1 to many")
    d.arrow((1802, 970), (1802, 1050), label="1 to many")
    d.save("erd.png")


def state_diagram() -> None:
    d = Diagram("Video Status State Diagram", 1700, 900)
    nodes = {
        "start": (120, 420, 210, 510, "Start"),
        "uploaded": (360, 390, 610, 535, "Uploaded"),
        "processing": (760, 390, 1040, 535, "Processing"),
        "analyzed": (1190, 250, 1440, 395, "Analyzed"),
        "failed": (1190, 560, 1440, 705, "Failed"),
        "archived": (1450, 250, 1630, 395, "Archived"),
    }
    d.ellipse(nodes["start"][:4], "Start", COLORS["green"])
    for key in ["uploaded", "processing", "analyzed", "failed", "archived"]:
        fill = COLORS["green"] if key == "analyzed" else COLORS["red"] if key == "failed" else COLORS["pale_blue"]
        d.box(nodes[key][:4], nodes[key][4], fill)
    d.arrow((210, 465), (360, 465))
    d.arrow((610, 465), (760, 465), label="analysis requested")
    d.arrow((1040, 430), (1190, 325), label="success")
    d.arrow((1040, 505), (1190, 635), label="failure")
    d.arrow((1190, 635), (1040, 505), label="retry")
    d.arrow((1315, 250), (1315, 180), label="reanalyze")
    d.arrow((1315, 180), (900, 390))
    d.arrow((1440, 325), (1450, 325), label="cleanup")
    d.save("video_status_state_diagram.png")


def component() -> None:
    d = Diagram("Component Diagram", 2400, 1660)

    def group(xy, title: str, items: list[str], cols: int = 2):
        x1, y1, x2, y2 = xy
        d.draw.rounded_rectangle(xy, 26, fill="#FBFDFF", outline=COLORS["blue"], width=4)
        d.text((x1 + 24, y1 + 20, x2 - 24, y1 + 72), title, SUBTITLE, align="left")
        item_w = (x2 - x1 - 80 - (cols - 1) * 26) // cols
        item_h = 66
        for idx, item in enumerate(items):
            col = idx % cols
            row = idx // cols
            bx1 = x1 + 40 + col * (item_w + 26)
            by1 = y1 + 105 + row * 92
            d.box((bx1, by1, bx1 + item_w, by1 + item_h), item, COLORS["gray"], fnt=SMALL_BOLD, radius=12)

    group((120, 160, 1120, 420), "API Layer", [
        "videos.py routes",
        "Pydantic schemas",
        "error response mapper",
        "request validation",
    ])
    group((120, 500, 1120, 875), "Application Services", [
        "video_storage.py",
        "video_processor.py",
        "timeline_builder.py",
        "question_answerer.py",
        "status workflow",
        "evidence retrieval",
    ])
    group((120, 955, 1120, 1200), "Domain Layer", [
        "entities.py",
        "statuses.py",
        "errors.py",
        "evidence types",
    ])
    group((120, 1280, 1120, 1548), "Persistence Layer", [
        "video_repository.py",
        "db/models.py",
        "SQLite metadata",
        "migration-ready schema",
    ])
    group((1300, 500, 2280, 990), "Infrastructure Adapters", [
        "audio_extractor.py",
        "transcriber.py",
        "frame_extractor.py",
        "scene_detector.py",
        "frame_analyzer.py",
        "file storage adapter",
    ])
    group((1300, 1080, 2280, 1548), "External Tools and APIs", [
        "FFmpeg",
        "OpenCV",
        "PySceneDetect",
        "OpenAI transcription",
        "Vision-language model",
        "Local file system",
    ])

    d.arrow((620, 420), (620, 500), label="calls services")
    d.arrow((620, 875), (620, 955), label="uses domain model")
    d.arrow((620, 1200), (620, 1280), label="persists through repository")
    d.arrow((1120, 690), (1300, 690), label="uses adapters")
    d.arrow((1790, 990), (1790, 1080), label="wraps")
    d.orthogonal_arrow([(1300, 1320), (1215, 1320), (1215, 1395), (1120, 1395)], label="file paths and metadata")
    d.save("component_diagram.png")


def deployment() -> None:
    d = Diagram("Deployment Diagram", 2200, 1250)
    d.draw.rounded_rectangle((100, 170, 1420, 1080), 30, fill="#FBFDFF", outline=COLORS["blue"], width=4)
    d.text((130, 205, 1390, 265), "Developer Laptop", SUBTITLE, align="left")

    d.draw.rounded_rectangle((170, 315, 1350, 560), 24, fill=COLORS["pale_blue"], outline=COLORS["blue"], width=3)
    d.text((195, 340, 1325, 390), "Application Runtime", SUBTITLE, align="left")
    d.box((250, 420, 560, 510), "Browser /\nSwagger UI", COLORS["white"], fnt=SMALL_BOLD)
    d.box((700, 395, 1100, 535), "FastAPI App\nUvicorn + Python", COLORS["white"], fnt=SMALL_BOLD)

    d.draw.rounded_rectangle((170, 685, 1350, 1015), 24, fill=COLORS["pale_blue"], outline=COLORS["blue"], width=3)
    d.text((195, 710, 1325, 760), "Local Processing and Storage", SUBTITLE, align="left")
    d.box((245, 835, 555, 940), "Local Data\nuploads, audio, frames", COLORS["white"], fnt=SMALL_BOLD)
    d.box((675, 835, 985, 940), "SQLite\nDatabase File", COLORS["white"], fnt=SMALL_BOLD)
    d.box((1065, 835, 1295, 940), "FFmpeg +\nPython Packages", COLORS["white"], fnt=SMALL_BOLD)

    d.draw.rounded_rectangle((1570, 390, 2070, 760), 30, fill="#FBFDFF", outline=COLORS["blue"], width=4)
    d.text((1595, 425, 2045, 485), "External AI Provider", SUBTITLE, align="left")
    d.box((1645, 585, 1995, 690), "Transcription and\nVision APIs", COLORS["light_blue"], fnt=SMALL_BOLD)

    d.arrow((560, 465), (700, 465), label="HTTP localhost")
    d.orthogonal_arrow([(900, 535), (900, 650), (900, 685)], label="local files, metadata, processing")
    d.orthogonal_arrow([(1100, 435), (1490, 435), (1490, 620), (1645, 620)], label="HTTPS API calls")
    d.orthogonal_arrow([(1645, 670), (1490, 670), (1490, 500), (1100, 500)], label="AI results")
    d.save("deployment_diagram.png")


def api_integration_swimlane() -> None:
    d = Diagram("API and Integration Swimlane Diagram", 2700, 1540)
    left = 90
    lane_label_w = 72
    content_left = left + lane_label_w
    right = 2610
    top = 140
    lane_h = 235
    lanes = [
        ("User / API Client", top, top + lane_h),
        ("FastAPI Backend", top + lane_h, top + lane_h * 2),
        ("Processing Services", top + lane_h * 2, top + lane_h * 3),
        ("External Tools / AI APIs", top + lane_h * 3, top + lane_h * 4),
        ("SQLite + Local Files", top + lane_h * 4, top + lane_h * 5),
    ]

    d.draw.rectangle((left, top, right, lanes[-1][2]), outline=COLORS["line"], width=4)
    d.draw.line((content_left, top, content_left, lanes[-1][2]), fill=COLORS["line"], width=3)
    for label, y1, y2 in lanes:
        d.draw.rectangle((left, y1, content_left, y2), fill="#FBFDFF", outline=COLORS["line"], width=2)
        d.draw.line((content_left, y2, right, y2), fill=COLORS["line"], width=3)
        txt = Image.new("RGBA", (lane_h, lane_label_w), (255, 255, 255, 0))
        td = ImageDraw.Draw(txt)
        bbox = td.textbbox((0, 0), label, font=SMALL_BOLD)
        td.text(((lane_h - (bbox[2] - bbox[0])) / 2, (lane_label_w - (bbox[3] - bbox[1])) / 2), label, font=SMALL_BOLD, fill=COLORS["ink"])
        rotated = txt.rotate(90, expand=True)
        d.image.paste(rotated, (left + 6, y1 + (lane_h - rotated.height) // 2), rotated)

    user_y = (lanes[0][1] + lanes[0][2]) // 2
    api_y = (lanes[1][1] + lanes[1][2]) // 2
    service_y = (lanes[2][1] + lanes[2][2]) // 2
    external_y = (lanes[3][1] + lanes[3][2]) // 2
    storage_y = (lanes[4][1] + lanes[4][2]) // 2

    # Client requests are aligned vertically above the matching API owner.
    d.box((285, user_y - 42, 555, user_y + 42), "Upload Video\nPOST /videos/upload", COLORS["white"], outline=COLORS["line"], radius=12, fnt=SMALL_BOLD)
    d.box((1030, user_y - 42, 1295, user_y + 42), "Start Analysis\nPOST /analyze", COLORS["white"], outline=COLORS["line"], radius=12, fnt=SMALL_BOLD)
    d.box((1390, user_y - 42, 1660, user_y + 42), "Check Status /\nView Timeline", COLORS["white"], outline=COLORS["line"], radius=12, fnt=SMALL_BOLD)
    d.box((1755, user_y - 42, 2025, user_y + 42), "Ask Question\nPOST /ask", COLORS["white"], outline=COLORS["line"], radius=12, fnt=SMALL_BOLD)
    d.box((2140, user_y - 42, 2460, user_y + 42), "Receive JSON\nwith timestamps", COLORS["white"], outline=COLORS["line"], radius=12, fnt=SMALL_BOLD)

    d.event_circle(220, api_y)
    d.box((285, api_y - 50, 555, api_y + 50), "Receive Upload\nRequest", COLORS["white"], outline=COLORS["line"], radius=12, fnt=SMALL_BOLD)
    d.box((655, api_y - 50, 925, api_y + 50), "Validate File\nCreate Video ID", COLORS["white"], outline=COLORS["line"], radius=12, fnt=SMALL_BOLD)
    d.box((1030, api_y - 50, 1295, api_y + 50), "Run Analyze\nEndpoint", COLORS["white"], outline=COLORS["line"], radius=12, fnt=SMALL_BOLD)
    d.box((1390, api_y - 50, 1660, api_y + 50), "Return Status\nor Timeline", COLORS["white"], outline=COLORS["line"], radius=12, fnt=SMALL_BOLD)
    d.box((1755, api_y - 50, 2025, api_y + 50), "Run Ask\nEndpoint", COLORS["white"], outline=COLORS["line"], radius=12, fnt=SMALL_BOLD)
    d.box((2140, api_y - 50, 2460, api_y + 50), "Return Answer\nand Evidence", COLORS["white"], outline=COLORS["line"], radius=12, fnt=SMALL_BOLD)
    d.event_circle(2545, api_y)

    d.box((655, service_y - 50, 925, service_y + 50), "VideoStorage\nService", COLORS["pale_blue"], outline=COLORS["blue"], radius=12, fnt=SMALL_BOLD)
    d.box((1030, service_y - 50, 1295, service_y + 50), "VideoProcessor\nService", COLORS["pale_blue"], outline=COLORS["blue"], radius=12, fnt=SMALL_BOLD)
    d.box((1390, service_y - 50, 1660, service_y + 50), "TimelineBuilder\nService", COLORS["pale_blue"], outline=COLORS["blue"], radius=12, fnt=SMALL_BOLD)
    d.box((1755, service_y - 50, 2025, service_y + 50), "QuestionAnswerer\nService", COLORS["pale_blue"], outline=COLORS["blue"], radius=12, fnt=SMALL_BOLD)

    d.box((875, external_y - 48, 1095, external_y + 48), "FFmpeg\nAudio", COLORS["white"], outline=COLORS["line"], radius=12, fnt=SMALL_BOLD)
    d.box((1140, external_y - 48, 1410, external_y + 48), "OpenCV /\nPySceneDetect", COLORS["white"], outline=COLORS["line"], radius=12, fnt=SMALL_BOLD)
    d.box((1455, external_y - 48, 1705, external_y + 48), "OpenAI\nTranscription", COLORS["white"], outline=COLORS["line"], radius=12, fnt=SMALL_BOLD)
    d.box((1760, external_y - 48, 2060, external_y + 48), "Vision /\nLanguage Model", COLORS["white"], outline=COLORS["line"], radius=12, fnt=SMALL_BOLD)

    d.box((380, storage_y - 48, 650, storage_y + 48), "Store Uploaded\nVideo File", COLORS["gray"], outline=COLORS["line"], radius=12, fnt=SMALL_BOLD)
    d.box((705, storage_y - 48, 970, storage_y + 48), "Store Video\nMetadata", COLORS["gray"], outline=COLORS["line"], radius=12, fnt=SMALL_BOLD)
    d.box((1270, storage_y - 48, 1635, storage_y + 48), "Save Transcript,\nFrames, Scenes,\nTimeline", COLORS["gray"], outline=COLORS["line"], radius=12, fnt=SMALL_BOLD)
    d.box((1745, storage_y - 48, 2055, storage_y + 48), "Read Stored\nVideo Memory", COLORS["gray"], outline=COLORS["line"], radius=12, fnt=SMALL_BOLD)

    flow = [
        ((244, api_y), (285, api_y)),
        ((555, api_y), (655, api_y)),
        ((925, api_y), (1030, api_y)),
        ((1295, api_y), (1390, api_y)),
        ((1660, api_y), (1755, api_y)),
        ((2025, api_y), (2140, api_y)),
        ((2460, api_y), (2521, api_y)),
    ]
    for start, end in flow:
        d.arrow(start, end, fill=COLORS["line"], width=3)

    dashed = "#64748B"
    # Vertical request ownership lines.
    d.arrow((420, user_y + 42), (420, api_y - 50), fill=dashed, width=2, dashed=True)
    d.arrow((1162, user_y + 42), (1162, api_y - 50), fill=dashed, width=2, dashed=True)
    d.arrow((1525, user_y + 42), (1525, api_y - 50), fill=dashed, width=2, dashed=True)
    d.arrow((1890, user_y + 42), (1890, api_y - 50), fill=dashed, width=2, dashed=True)
    d.arrow((2300, api_y - 50), (2300, user_y + 42), fill=dashed, width=2, dashed=True)

    # Backend to service ownership.
    d.arrow((790, api_y + 50), (790, service_y - 50), fill=dashed, width=2, dashed=True)
    d.arrow((1162, api_y + 50), (1162, service_y - 50), fill=dashed, width=2, dashed=True)
    d.arrow((1525, api_y + 50), (1525, service_y - 50), fill=dashed, width=2, dashed=True)
    d.arrow((1890, api_y + 50), (1890, service_y - 50), fill=dashed, width=2, dashed=True)

    # Storage writes and reads are routed vertically or through short horizontal segments.
    d.orthogonal_arrow([(790, service_y + 50), (790, storage_y - 92), (520, storage_y - 92), (520, storage_y - 48)], fill=dashed, width=2, label="write file")
    d.arrow((835, service_y + 50), (835, storage_y - 48), fill=dashed, width=2, dashed=True)
    d.arrow((1525, service_y + 50), (1525, storage_y - 48), fill=dashed, width=2, dashed=True)
    d.arrow((1890, service_y + 50), (1890, storage_y - 48), fill=dashed, width=2, dashed=True)

    # External tool fan-out uses one bus, avoiding diagonal crossings.
    bus_y = external_y - 88
    d.arrow((1162, service_y + 50), (1162, bus_y), fill=dashed, width=2, dashed=True, label="process media")
    d.draw.line((985, bus_y, 1908, bus_y), fill=dashed, width=2)
    for x in [985, 1275, 1580, 1908]:
        d.arrow((x, bus_y), (x, external_y - 48), fill=dashed, width=2, dashed=True)
    d.orthogonal_arrow([(1908, service_y + 50), (1908, external_y - 48)], fill=dashed, width=2)

    # Timeline uses processed outputs; ask uses stored memory plus model result.
    d.orthogonal_arrow([(1295, service_y), (1390, service_y)], fill=COLORS["line"], width=3, label="pipeline output")
    d.orthogonal_arrow([(2025, service_y), (2085, service_y), (2085, api_y + 50), (2140, api_y + 50)], fill=dashed, width=2, label="answer")

    d.text((300, 1355, 1220, 1405), "Solid arrows show the main REST flow. Dashed arrows show storage access, processing services, and external integration calls.", SMALL, fill=COLORS["muted"], align="left")
    d.text((1380, 1355, 2470, 1405), "The layout keeps upload, analysis, timeline retrieval, and question answering in separate vertical columns so each input and output is traceable.", SMALL, fill=COLORS["muted"], align="left")
    d.save("api_integration_swimlane.png")


def main() -> None:
    use_case()
    context()
    dfd()
    pipeline()
    activity()
    sequence_upload()
    sequence_ask()
    class_diagram()
    erd()
    state_diagram()
    component()
    deployment()
    api_integration_swimlane()
    print(f"Generated specification diagrams in {OUT}")


if __name__ == "__main__":
    main()
