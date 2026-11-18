"""Tk desktop workbench for importing, inspecting and exporting calibration jobs."""

import base64
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
import numpy as np

from .calibration import (
    CalibrationError, Chessboard, Intrinsics, calibrate_intrinsics, compare_truth, estimate_mount, read_image,
)
from .data import list_images, load_pose_pairs, read_json, write_json
from .demo import DEMO_BOARD, generate_demo


MODES = {
    "intrinsics": ("相机内参", "导入多张棋盘格照片，计算相机内参和畸变。"),
    "eye-in-hand": ("眼在手上", "相机随末端运动，棋盘格固定。输出相机 → 末端。"),
    "eye-to-hand": ("眼在手外", "相机固定，棋盘格随末端运动。输出相机 → 基座。"),
}

BG = "#edf2f7"
CARD = "#ffffff"
DARK = "#13263b"
INK = "#182c42"
MUTED = "#50657b"
ACCENT = "#0e6859"
PALE = "#e5f3ee"
BORDER = "#dce5ed"
FONT = ("Microsoft YaHei UI", 10)


class Workbench:
    def __init__(self, window, demo_root, executor):
        self.window = window
        self.demo_root = Path(demo_root)
        self.executor = executor
        self.mode = "eye-in-hand"
        self.images = None
        self.poses = None
        self.intrinsics = None
        self.truth = None
        self.latest_intrinsics = None
        self.result = None
        self.failed_views = None
        self.image_paths = {}
        self.preview_image = None
        self.busy = False
        self.controls = []
        self.mode_buttons = {}
        self.board_vars = [tk.StringVar(value=str(value)) for value in (9, 6, 24)]
        self.threshold = tk.StringVar(value="1.0")
        self.status = tk.StringVar(value="请选择数据，或先载入演示数据。")
        self.sample_count = tk.StringVar(value="0 张照片")

        window.title("Robot Auto Calibration · 机器人相机标定")
        window.geometry("1180x780")
        window.minsize(990, 690)
        window.configure(bg=BG)
        window.option_add("*Font", FONT)
        self._theme()
        self._layout()
        self._refresh_inputs()

    def _theme(self):
        style = ttk.Style(self.window)
        style.theme_use("clam")
        style.configure(
            "Calibration.Treeview", font=FONT, rowheight=29,
            background=CARD, fieldbackground=CARD, foreground=INK, borderwidth=0
        )
        style.configure(
            "Calibration.Treeview.Heading", font=(FONT[0], 10, "bold"),
            background=BG, foreground=INK, relief="flat", padding=6
        )
        style.map("Calibration.Treeview", background=[("selected", PALE)], foreground=[("selected", INK)])

    @staticmethod
    def _label(parent, text="", *, color=INK, bg=CARD, size=10, weight="normal", **kwargs):
        return tk.Label(parent, text=text, fg=color, bg=bg, font=(FONT[0], size, weight), **kwargs)

    def _button(self, parent, label, action, *, primary=False, small=False):
        button = tk.Button(
            parent, text=label, command=action, relief="flat", bd=0, cursor="hand2",
            padx=10 if small else 15, pady=5 if small else 8,
            bg=ACCENT if primary else PALE, fg=CARD if primary else ACCENT,
            activebackground="#075447" if primary else "#d6ebe4",
            activeforeground=CARD if primary else INK,
            disabledforeground="#8b9ba4", font=(FONT[0], 10, "bold"),
        )
        self.controls.append(button)
        return button

    def _layout(self):
        header = tk.Frame(self.window, bg=DARK, padx=26, pady=17)
        header.pack(fill="x")
        self._label(header, "机器人相机标定", color=CARD, bg=DARK, size=21, weight="bold").pack(side="left")
        self._button(header, "载入演示数据", self.load_demo, primary=True).pack(side="right")

        body = tk.Frame(self.window, bg=BG, padx=22, pady=17)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, minsize=326)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)
        nav = tk.Frame(body, bg=BG)
        nav.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 13))
        for mode, (label, _) in MODES.items():
            button = self._button(nav, label, lambda value=mode: self.select_mode(value))
            button.pack(side="left", padx=(0, 8))
            self.mode_buttons[mode] = button

        sidebar = tk.Frame(body, bg=CARD, padx=17, pady=16, highlightbackground=BORDER, highlightthickness=1)
        sidebar.grid(row=1, column=0, sticky="nsew", padx=(0, 14))
        self._label(sidebar, "数据输入", size=14, weight="bold").pack(anchor="w")
        self.mode_hint = self._label(sidebar, color=MUTED, wraplength=265, justify="left", anchor="w")
        self.mode_hint.pack(fill="x", pady=(5, 14))

        self.photo_row, self.photo_hint = self._file_input(sidebar, "图像目录", self.choose_images)
        self.pose_row, self.pose_hint = self._file_input(sidebar, "末端位姿 JSON", self.choose_poses)
        self.intrinsic_row, self.intrinsic_hint = self._file_input(sidebar, "相机内参 JSON", self.choose_intrinsics)
        self.last_intrinsics = self._button(sidebar, "使用本次计算的内参", self.use_last_intrinsics, small=True)
        self.last_intrinsics.pack(anchor="w", pady=(0, 8))

        self._label(sidebar, "棋盘格 · 内角点数", weight="bold").pack(anchor="w", pady=(6, 5))
        board_box = tk.Frame(sidebar, bg=CARD)
        board_box.pack(fill="x")
        for index, (title, value) in enumerate(zip(("列", "行", "格边长 (mm)"), self.board_vars, strict=True)):
            field = tk.Frame(board_box, bg=CARD)
            field.grid(row=0, column=index, sticky="ew", padx=(0, 8))
            self._label(field, title, color=MUTED, size=9).pack(anchor="w")
            self._entry(field, value, 8).pack(anchor="w", pady=(2, 0))

        self.threshold_row = tk.Frame(sidebar, bg=CARD)
        self.threshold_row.pack(fill="x", pady=(13, 0))
        self._label(self.threshold_row, "重投影误差上限 (px)", color=MUTED).pack(side="left")
        self._entry(self.threshold_row, self.threshold, 7).pack(side="right")

        self.actions = tk.Frame(sidebar, bg=CARD)
        self.actions.pack(side="bottom", fill="x", pady=(12, 0))
        self._button(self.actions, "运行标定", self.run, primary=True).pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.export = self._button(self.actions, "导出 JSON", self.export_result)
        self.export.pack(side="right")

        right = tk.Frame(body, bg=BG)
        right.grid(row=1, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        cards = tk.Frame(right, bg=BG)
        cards.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        cards.columnconfigure(0, weight=1, uniform="top")
        cards.columnconfigure(1, weight=1, uniform="top")

        visual = tk.Frame(cards, bg=DARK, padx=12, pady=10)
        visual.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._label(visual, "图像预览", color="#d2e1eb", bg=DARK, weight="bold").pack(anchor="w")
        self.canvas = tk.Canvas(visual, bg="#1b344c", height=185, highlightthickness=0)
        self.canvas.pack(fill="x", pady=(7, 2))
        self.preview_path = None
        self.canvas.bind("<Configure>", lambda _event: self._preview(self.preview_path))

        outcome = tk.Frame(cards, bg=CARD, padx=14, pady=12, highlightbackground=BORDER, highlightthickness=1)
        outcome.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self._label(outcome, "标定结果", size=14, weight="bold").pack(anchor="w")
        self.summary = self._label(outcome, color=MUTED, anchor="nw", justify="left", wraplength=325)
        self.summary.pack(fill="both", expand=True, anchor="w", pady=(9, 0))
        self.summary.bind("<Configure>", lambda event: self.summary.configure(wraplength=max(170, event.width - 5)))

        samples = tk.Frame(right, bg=CARD, padx=13, pady=12, highlightbackground=BORDER, highlightthickness=1)
        samples.grid(row=1, column=0, sticky="nsew")
        samples.rowconfigure(1, weight=1)
        samples.columnconfigure(0, weight=1)
        row_header = tk.Frame(samples, bg=CARD)
        row_header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self._label(row_header, "样本检查", size=14, weight="bold").pack(side="left")
        self._label(row_header, textvariable=self.sample_count, color=MUTED).pack(side="right")
        self.table = ttk.Treeview(samples, columns=("state", "error", "reason"), style="Calibration.Treeview", selectmode="browse")
        for column, label, width in (("#0", "图像", 128), ("state", "状态", 65), ("error", "RMS (px)", 90), ("reason", "原因", 200)):
            self.table.heading(column, text=label, anchor="w")
            self.table.column(column, width=width, minwidth=50, stretch=column in ("#0", "reason"))
        self.table.tag_configure("rejected", foreground="#9a4336")
        self.table.bind("<<TreeviewSelect>>", self._select_photo)
        self.table.grid(row=1, column=0, sticky="nsew")
        scroller = ttk.Scrollbar(samples, command=self.table.yview)
        scroller.grid(row=1, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scroller.set)

        footer = self._label(self.window, textvariable=self.status, bg=BG, color=MUTED, anchor="w", padx=23)
        footer.pack(fill="x", pady=(0, 10))

    def _file_input(self, parent, title, action):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", pady=(0, 9))
        self._label(row, title, weight="bold").pack(side="top", anchor="w")
        values = tk.Frame(row, bg=CARD)
        values.pack(fill="x", pady=(3, 0))
        label = self._label(values, color=MUTED, wraplength=195, justify="left", anchor="w")
        label.pack(side="left", fill="x", expand=True)
        self._button(values, "选择", action, small=True).pack(side="right")
        return row, label

    def _entry(self, parent, variable, width):
        box = tk.Entry(
            parent, textvariable=variable, width=width, relief="flat", bd=4, bg=BG,
            fg=INK, highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT,
        )
        self.controls.append(box)
        variable.trace_add("write", lambda *_: self._reset_result())
        return box

    def _refresh_inputs(self):
        self.mode_hint.configure(text=MODES[self.mode][1])
        for mode, button in self.mode_buttons.items():
            button.configure(bg=ACCENT if mode == self.mode else PALE, fg=CARD if mode == self.mode else ACCENT)
        if self.mode == "intrinsics":
            for widget in (self.pose_row, self.intrinsic_row, self.last_intrinsics, self.threshold_row):
                widget.pack_forget()
        else:
            self.pose_row.pack(fill="x", after=self.photo_row, pady=(0, 9))
            self.intrinsic_row.pack(fill="x", after=self.pose_row, pady=(0, 9))
            self.last_intrinsics.pack(anchor="w", after=self.intrinsic_row, pady=(0, 8))
            self.threshold_row.pack(fill="x", pady=(13, 0), before=self.actions)
        self.photo_hint.configure(text=self.images.name if self.images else "尚未选择图像目录")
        self.pose_hint.configure(text=self.poses.name if self.poses else "按图像文件名配对")
        intrinsic_name = self.intrinsics.name if isinstance(self.intrinsics, Path) else "本次计算的内参"
        self.intrinsic_hint.configure(text=intrinsic_name if self.intrinsics is not None else "导入已知相机内参")
        self.last_intrinsics.configure(state="normal" if self.latest_intrinsics and not self.busy else "disabled")
        self.export.configure(state="normal" if self.result and not self.busy else "disabled")

    def _reset_result(self):
        self.result = None
        self.failed_views = None
        if hasattr(self, "summary"):
            self.summary.configure(text="运行后显示标定参数和误差。")
            self.export.configure(state="disabled")
            self._update_table()

    def select_mode(self, mode):
        if mode == self.mode or self.busy:
            return
        self.mode = mode
        if self.truth:
            self.images = self.poses = self.intrinsics = self.truth = None
        self._reset_result()
        self._refresh_inputs()
        if self.images is None:
            self._preview(None)
        self.status.set(f"已选择{MODES[mode][0]}。")

    def choose_images(self):
        chosen = filedialog.askdirectory(parent=self.window, title="选择棋盘格照片目录")
        if chosen:
            self.images, self.truth = Path(chosen), None
            self._reset_result()
            self._refresh_inputs()
            self._preview_first()

    def _choose_json(self, title):
        chosen = filedialog.askopenfilename(parent=self.window, title=title, filetypes=[("JSON", "*.json")])
        return Path(chosen) if chosen else None

    def choose_poses(self):
        chosen = self._choose_json("选择图像与末端位姿配对文件")
        if chosen:
            self.poses, self.truth = chosen, None
            self._reset_result()
            self._refresh_inputs()

    def choose_intrinsics(self):
        chosen = self._choose_json("选择相机内参文件")
        if chosen:
            self.intrinsics, self.truth = chosen, None
            self._reset_result()
            self._refresh_inputs()

    def use_last_intrinsics(self):
        self.intrinsics, self.truth = self.latest_intrinsics, None
        self._reset_result()
        self._refresh_inputs()

    def load_demo(self):
        mode = "eye-in-hand" if self.mode == "intrinsics" else self.mode
        folder = self.demo_root / mode

        def prepare():
            if not (folder / "truth.json").exists():
                generate_demo(folder, mode)
            return folder

        self._start(prepare, self._demo_loaded, "正在生成演示数据…")

    def _demo_loaded(self, directory):
        for variable, value in zip(self.board_vars, (DEMO_BOARD.columns, DEMO_BOARD.rows, DEMO_BOARD.square_mm), strict=True):
            variable.set(str(value))
        self.threshold.set("1.0")
        self.images = directory / "images"
        self.poses = directory / "poses.json"
        self.intrinsics = directory / "intrinsics.json"
        self.truth = directory / "truth.json"
        self._reset_result()
        self._refresh_inputs()
        self._preview_first()
        self.status.set("已载入 15 张模拟照片。点击「运行标定」查看结果。")

    def run(self):
        try:
            if self.images is None:
                raise ValueError("请先选择棋盘格照片所在目录。")
            values = [field.get() for field in self.board_vars]
            try:
                board = Chessboard(int(values[0]), int(values[1]), float(values[2]))
            except ValueError as exc:
                raise ValueError("请检查棋盘格的内角点列数、行数和方格边长。") from exc
            mode, image_directory = self.mode, self.images
            poses, intrinsics, truth = self.poses, self.intrinsics, self.truth
            threshold = 1.0
            if mode != "intrinsics":
                if poses is None or intrinsics is None:
                    raise ValueError("手眼标定需要末端位姿文件和相机内参。")
                try:
                    threshold = float(self.threshold.get())
                except ValueError as exc:
                    raise ValueError("重投影误差上限应填写数值。") from exc
        except ValueError as exc:
            self._show_error(exc)
            return

        def calibrate():
            if mode == "intrinsics":
                return calibrate_intrinsics(list_images(image_directory), board)
            data = read_json(intrinsics) if isinstance(intrinsics, Path) else intrinsics
            pairs = load_pose_pairs(poses, image_directory)
            result = estimate_mount(mode, pairs, board, Intrinsics.from_record(data), threshold)
            if truth is not None:
                result["synthetic_truth_error"] = compare_truth(result, read_json(truth))
            return result

        self._reset_result()
        self._start(calibrate, self._show_result, "正在检测角点和计算标定参数…")

    def _start(self, operation, on_success, label):
        self.busy = True
        self.status.set(label)
        for control in self.controls:
            control.configure(state="disabled")
        future = self.executor.submit(operation)

        def check():
            if not future.done():
                self.window.after(80, check)
                return
            self.busy = False
            for control in self.controls:
                control.configure(state="normal")
            self._refresh_inputs()
            try:
                on_success(future.result())
            except Exception as exc:
                self._show_error(exc)

        self.window.after(80, check)

    def _show_error(self, error):
        if isinstance(error, CalibrationError):
            self.failed_views = error.views
            self._update_table()
            self.status.set("求解未完成。样本检查表保留了本次图像的处理结果。")
        else:
            self.status.set("操作未完成。请根据提示检查输入后重试。")
        messagebox.showerror("标定工作台", str(error), parent=self.window)

    def _show_result(self, result):
        self.result = result
        if self.mode == "intrinsics":
            self.latest_intrinsics = result
            matrix = result["camera_matrix"]
            summary = (
                f"整体重投影误差  {result['reprojection_rms_px']:.4f} px\n\n"
                f"焦距 fx / fy  {matrix[0][0]:.2f} / {matrix[1][1]:.2f} px\n"
                f"主点 cx / cy  {matrix[0][2]:.2f} / {matrix[1][2]:.2f} px\n\n"
                "内参矩阵与畸变系数可导出为 JSON。"
            )
        else:
            matrix = np.asarray(result["matrix"])
            translation = matrix[:3, 3]
            rotation = np.rad2deg(cv2.Rodrigues(matrix[:3, :3])[0]).ravel()
            destination = "末端" if result["to_frame"] == "gripper" else "基座"
            spread = result["in_sample_consistency"]
            summary = (
                f"相机 → {destination}\n"
                f"平移 X / Y / Z (mm)\n{' / '.join(f'{value:.3f}' for value in translation)}\n"
                f"旋转向量 (°)\n{' / '.join(f'{value:.3f}' for value in rotation)}\n\n"
                f"拟合样本板位置离散  {spread['position_rms_about_centroid_mm']:.3f} mm\n"
                f"拟合样本板姿态离散  {spread['mean_pairwise_rotation_deg']:.3f}°"
            )
            if "synthetic_truth_error" in result:
                error = result["synthetic_truth_error"]
                summary += f"\n\n仿真真值误差  {error['translation_mm']:.3f} mm / {error['rotation_deg']:.3f}°"
        self.summary.configure(text=summary)
        self._refresh_inputs()
        self._update_table()
        self.status.set("标定完成。可选择任一样本预览，或导出全部参数和质检结果。")

    def _update_table(self):
        self.table.delete(*self.table.get_children())
        self.image_paths = {}
        if self.images is None:
            self.sample_count.set("0 张照片")
            return
        try:
            files = list_images(self.images)
        except OSError:
            self.sample_count.set("无法读取图像目录")
            return
        self.image_paths = {path.name: path for path in files}
        records = self.result["views"] if self.result else self.failed_views
        inspected = records is not None
        if not inspected:
            records = [{"image": name} for name in self.image_paths]
        for record in records:
            accepted = record.get("accepted")
            error = record.get("reprojection_rms_px")
            values = (
                "待检查" if accepted is None else "有效" if accepted else "拒绝",
                f"{error:.4f}" if error is not None else "—", record.get("reason", ""),
            )
            self.table.insert("", "end", text=record["image"], values=values, tags=("rejected",) if accepted is False else ())
        if inspected:
            self.sample_count.set(f"有效 {sum(row['accepted'] for row in records)} / {len(records)}")
        else:
            self.sample_count.set(f"{len(records)} 张照片")

    def _select_photo(self, _event):
        selection = self.table.selection()
        if selection:
            self._preview(self.image_paths.get(self.table.item(selection[0], "text")))

    def _preview_first(self):
        self._preview(next(iter(self.image_paths.values()), None))

    def _preview(self, path):
        self.preview_path = path
        self.canvas.delete("all")
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if width < 20 or height < 20:
            return
        label = "选择图像目录后预览照片"
        if path:
            try:
                image = read_image(path, color=True)
                scale = min(width / image.shape[1], height / image.shape[0])
                resized = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
                success, encoded = cv2.imencode(".png", resized)
                if success:
                    self.preview_image = tk.PhotoImage(data=base64.b64encode(encoded))
                    self.canvas.create_image(width // 2, height // 2, image=self.preview_image)
                    return
            except (OSError, ValueError, cv2.error, tk.TclError):
                pass
            label = "该图像无法预览"
        self.canvas.create_text(width // 2, height // 2, text=label, fill="#bdcfdf", font=FONT)

    def export_result(self):
        if self.result is None:
            return
        chosen = filedialog.asksaveasfilename(
            parent=self.window, defaultextension=".json", filetypes=[("JSON", "*.json")],
            initialfile=f"{self.mode}-result.json", title="导出标定结果",
        )
        if chosen:
            try:
                write_json(chosen, self.result)
                self.status.set(f"已导出 {Path(chosen).name}。")
            except (OSError, ValueError) as exc:
                self._show_error(exc)


def launch():
    window = tk.Tk()
    with TemporaryDirectory(prefix="robot-calibration-") as demo_root, ThreadPoolExecutor(max_workers=1) as executor:
        Workbench(window, demo_root, executor)
        window.mainloop()
