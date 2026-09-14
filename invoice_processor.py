# -*- coding: utf-8 -*-
# 发票小助手 (Invoice Sorter) v3.1
# Supports PDF / JPG / PNG / BMP / TIFF / WEBP invoices.
# Copyright (c) 2026 yingxiang.he@zkh.com. All rights reserved.

import os
import re
import shutil
import sys
import threading
import queue
import time
import tempfile
from datetime import datetime
import traceback

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# PyMuPDF 用于 PDF 文本提取与页面渲染（用于扫描件 OCR）
try:
    import pymupdf as fitz  # PyMuPDF
except Exception:  # pragma: no cover
    try:
        import fitz
    except Exception:
        fitz = None

# 资源路径兼容打包后环境（PyInstaller onefile 使用 _MEIPASS）
def _resource_path(rel_path):
    try:
        base = sys._MEIPASS
    except AttributeError:
        base = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base, rel_path)


# 设置 tkinter 窗口图标（打包后读取嵌入的 logo.ico）
def _set_window_icon(root):
    ico = _resource_path("logo.ico")
    if os.path.exists(ico):
        try:
            root.iconbitmap(ico)
        except Exception:
            pass
    # 同时尝试加载 PNG 作为图标照片（支持高分屏缩放）
    png = _resource_path("logo.png")
    if os.path.exists(png):
        try:
            icon_img = tk.PhotoImage(file=png)
            root.iconphoto(True, icon_img)
            root._app_icon = icon_img  # 防止被 GC
        except Exception:
            pass


# OCR 引擎懒加载（rapidocr-onnxruntime 体积小、无需外部二进制、中文识别好）
_ocr_engine = None
_ocr_import_error = None


def _get_ocr_engine():
    """懒加载 OCR 引擎单例（避免启动时拖慢、也避免未安装时报错）。"""
    global _ocr_engine, _ocr_import_error
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
        except Exception as e:  # pragma: no cover
            _ocr_import_error = e
            _ocr_engine = False  # 标记为不可用
    return _ocr_engine


# ==================== 支持的文件类型 ====================
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
PDF_EXTS = {".pdf"}
SUPPORTED_EXTS = IMAGE_EXTS | PDF_EXTS

FILE_DIALOG_TYPES = [
    ("发票文件", "*.pdf *.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp"),
    ("PDF 文件", "*.pdf"),
    ("图片文件", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp"),
    ("所有文件", "*.*"),
]


# ==================== 分类规则 ====================
# 内容关键词（货物或应税劳务、服务名称区域，优先级最高）
CONTENT_KEYWORDS = {
    "交通类": ["滴滴", "出租", "网约车", "高铁", "火车", "铁路", "机票", "航空", "飞机", "地铁", "公交",
              "加油", "汽油", "柴油", "停车", "过路费", "通行费", "ETC", "客运", "出行", "打车", "租车",
              "班车", "客运服务", "运输服务", "里程", "行程", "油费"],
    "餐饮类": ["餐饮", "餐费", "饮食", "外卖", "餐厅", "食品", "饭店", "酒楼", "美团", "饿了么", "小吃",
              "快餐", "茶", "咖啡", "奶茶", "餐饮服务", "团餐", "用餐"],
    "住宿类": ["住宿", "酒店", "宾馆", "旅馆", "客房", "房费", "民宿", "酒店服务", "住宿服务"],
    "办公类": ["办公", "打印", "复印", "文具", "耗材", "办公用品", "电脑", "软件", "IT", "设备", "家具",
              "打印机", "墨盒", "硒鼓", "纸张", "办公家具", "电脑配件", "键盘", "鼠标", "显示器",
              "电子设备", "硬件", "服务器", "网络设备"],
    "通讯类": ["话费", "通讯", "流量", "宽带", "电信", "移动", "联通", "手机", "通信", "充值", "套餐",
              "套餐费", "通话", "增值电信"],
    "物流类": ["快递", "物流", "运费", "货运", "邮寄", "顺丰", "圆通", "中通", "韵达", "申通", "邮政",
              "快递费", "运输", "配送"],
    "广告宣传类": ["广告", "宣传", "推广", "策划", "展会", "展位", "物料", "印刷"],
    "服务类": ["服务费", "咨询", "培训", "维修", "保养", "技术服务", "设计", "广告", "会议", "会展",
              "中介", "代理", "顾问", "审计", "律师", "法律服务", "检测", "认证", "评估"],
    "医疗类": ["医疗", "药品", "医药", "诊疗", "体检", "医院", "药店", "药房", "挂号", "门诊", "医疗器械"],
    "水电类": ["水费", "电费", "燃气", "煤气", "暖气", "物业", "房租", "租金", "水电", "热力", "停车费"],
    "差旅类": ["差旅", "出差", "差旅费"],
    "教育培训类": ["培训", "教育", "课程", "学费", "考试", "教材", "网课", "辅导", "学习", "认证培训"],
    "图书类": ["图书", "书籍", "教材", "出版物", "杂志", "期刊"],
}

# 开具单位（销售方）关键词（优先级次之）
SELLER_KEYWORDS = {
    "交通类": ["滴滴", "滴滴出行", "中国国家铁路集团", "中国铁路", "12306", "高德", "携程", "去哪儿",
              "同程", "航旅纵横", "东方航空", "南方航空", "中国国航", "海南航空", "航空公司", "地铁", "公交",
              "中石化", "中石油", "中国石化", "中国石油", "石化", "石油", "壳牌", "出租", "网约车"],
    "餐饮类": ["美团", "饿了么", "肯德基", "麦当劳", "必胜客", "海底捞", "星巴克", "瑞幸", "喜茶", "奈雪",
              "餐饮", "饭店", "酒楼", "餐厅", "食堂", "食品"],
    "住宿类": ["酒店", "宾馆", "民宿", "华住", "锦江", "如家", "亚朵", "洲际", "万豪", "希尔顿", "住宿"],
    "办公类": ["京东", "苏宁", "国美", "办公", "文具", "联想", "戴尔", "惠普", "微软", "Adobe", "天猫",
              "淘宝", "打印机", "耗材", "电子设备", "电脑", "软件"],
    "通讯类": ["中国移动", "中国联通", "中国电信", "移动", "联通", "电信", "通信"],
    "物流类": ["顺丰", "圆通", "中通", "韵达", "申通", "邮政", "德邦", "京东物流", "菜鸟", "物流", "快递"],
    "广告宣传类": ["广告", "传媒", "文化传播", "策划", "印刷"],
    "服务类": ["咨询", "顾问", "广告", "传媒", "设计", "会计师事务所", "律师事务所", "检测", "认证"],
    "医疗类": ["医院", "药店", "药房", "诊所", "医疗", "医药", "卫生"],
    "水电类": ["供水", "供电", "电力", "燃气", "水务", "热力", "物业", "电网", "自来水"],
    "教育培训类": ["培训", "教育", "学校", "学院", "大学", "学堂", "网课"],
    "图书类": ["书店", "图书", "出版", "当当", "文轩"],
}

# 排序：让"差旅类"等更具象的关键词先匹配时，避免被更宽泛的关键词提前命中。
# 这里通过"内容区优先 + 关键词长度优先"策略实现（见 classify_invoice）。


# ==================== 正则预编译 ====================
def _norm(text):
    """全角转半角 + 压缩空白，提升金额/日期匹配成功率。"""
    if not text:
        return ""
    out = []
    for ch in text:
        code = ord(ch)
        if code == 0x3000:
            out.append(' ')
        elif 0xFF01 <= code <= 0xFF5E:
            out.append(chr(code - 0xFEE0))
        else:
            out.append(ch)
    return ''.join(out)


AMOUNT_PATTERNS = [
    re.compile(r'价税合计[（(]?大写[)）]?.*?[（(]?小写[)）]?\s*[¥￥]?\s*([0-9,]+(?:\.[0-9]{1,2})?)', re.DOTALL),
    re.compile(r'价税合计[（(]?小写[)）]?\s*[¥￥]?\s*([0-9,]+(?:\.[0-9]{1,2})?)'),
    re.compile(r'[（(]?小写[)）]?\s*[¥￥]\s*([0-9,]+(?:\.[0-9]{1,2})?)'),
    re.compile(r'[（(]?小写[)）]?\s*([0-9,]+(?:\.[0-9]{1,2})?)\s*元'),
    re.compile(r'合计金额[（(]?小写[)）]?\s*[¥￥]?\s*([0-9,]+(?:\.[0-9]{1,2})?)'),
    re.compile(r'价税合计[：:]\s*[¥￥]?\s*([0-9,]+(?:\.[0-9]{1,2})?)'),
    re.compile(r'[¥￥]\s*([0-9,]+(?:\.[0-9]{1,2})?)'),
    re.compile(r'人民币[：:]?\s*[¥￥]?\s*([0-9,]+(?:\.[0-9]{1,2})?)'),
    re.compile(r'总计[：:]?\s*[¥￥]?\s*([0-9,]+(?:\.[0-9]{1,2})?)'),
    re.compile(r'([0-9,]+(?:\.[0-9]{1,2})?)\s*元'),
]

DATE_PATTERNS = [
    re.compile(r'开票日期[：:]\s*([0-9]{4})\s*年\s*([0-9]{1,2})\s*月\s*([0-9]{1,2})\s*日'),
    re.compile(r'开票日期[：:]\s*([0-9]{4})[-/.年]([0-9]{1,2})[-/.月]([0-9]{1,2})日?'),
    re.compile(r'([0-9]{4})\s*年\s*([0-9]{1,2})\s*月\s*([0-9]{1,2})\s*日'),
    re.compile(r'([0-9]{4})[-/]([0-9]{1,2})[-/]([0-9]{1,2})'),
    re.compile(r'([0-9]{4})[.·]([0-9]{1,2})[.·]([0-9]{1,2})'),
    re.compile(r'([0-9]{4})([0-9]{2})([0-9]{2})'),
]


# ==================== 文本提取 ====================
def ocr_text(img_input):
    """调用 OCR 引擎识别图片/图像字节，返回拼接文本。"""
    engine = _get_ocr_engine()
    if engine is None or engine is False:
        raise RuntimeError("OCR 引擎不可用，未安装 rapidocr-onnxruntime")
    result, _ = engine(img_input)
    if not result:
        return ""
    lines = []
    for item in result:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            lines.append(str(item[1]))
        elif hasattr(item, "txt"):
            lines.append(str(item.txt))
    return "\n".join(lines)


def extract_text_from_pdf(pdf_path):
    """PDF：优先提取文本层；无文本层（扫描件）则渲染页面 OCR。"""
    if fitz is None:
        raise RuntimeError("未安装 PyMuPDF，无法处理 PDF")
    doc = fitz.open(pdf_path)
    try:
        text_parts = []
        for page in doc:
            t = page.get_text()
            if t:
                text_parts.append(t)
        text = "\n".join(text_parts).strip()
        if text:
            return text

        # 文本层为空 -> 渲染前几页做 OCR
        for i, page in enumerate(doc):
            if i >= 3:
                break
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            png_bytes = pix.tobytes("png")
            t = ocr_text(png_bytes)
            if t:
                text_parts.append(t)
        return "\n".join(text_parts).strip() or None
    finally:
        doc.close()


def extract_text_from_image(img_path):
    """图片发票：直接 OCR。"""
    return ocr_text(img_path)


# ==================== 信息提取 ====================
def extract_amount(text):
    """提取价税合计金额，返回 '820.00' 格式字符串或 None。"""
    text = _norm(text or "")
    if not text:
        return None
    for pattern in AMOUNT_PATTERNS:
        m = pattern.search(text)
        if m:
            raw = m.group(1).replace(',', '').strip()
            try:
                value = float(raw)
            except ValueError:
                continue
            # 过滤明显异常值（如单价、税率等误匹配），价税合计通常合理
            if value <= 0:
                continue
            return f"{value:.2f}"
    return None


def extract_invoice_date(text, file_path=None):
    """提取开票日期，返回 'YYYY年M月'；失败回退文件修改时间。"""
    text = _norm(text or "")
    if text:
        for pattern in DATE_PATTERNS:
            m = pattern.search(text)
            if m:
                try:
                    year = int(m.group(1))
                    month = int(m.group(2))
                    if 1 <= month <= 12 and 1900 <= year <= 2100:
                        return f"{year}年{month}月"
                except (IndexError, ValueError):
                    continue

    if file_path and os.path.exists(file_path):
        try:
            mtime = os.path.getmtime(file_path)
            dt = datetime.fromtimestamp(mtime)
            return f"{dt.year}年{dt.month}月"
        except (OSError, ValueError):
            pass

    now = datetime.now()
    return f"{now.year}年{now.month}月"


def _extract_item_area(text):
    """提取货物或应税劳务、服务名称区域。"""
    m = re.search(
        r'(?:项目名称|货物或应税劳务[、,]?服务名称|货物或应税劳务服务名称)[：:]?(.*?)(?:规格型号|单位|数量|单价|金额|税率|税额|合计|备注)',
        text, re.DOTALL)
    return m.group(1) if m else ""


def _extract_seller_area(text):
    """提取销售方信息区域。"""
    m = re.search(
        r'(?:销售方信息|销售方)[：:]?(.*?)(?:购买方|项目名称|货物|价税合计|备注|合计|$)',
        text, re.DOTALL)
    return m.group(1) if m else ""


def _best_category(text, keyword_map):
    """在给定文本中，跨所有分类按『最长关键词』优先匹配，返回首个命中分类。
    长关键词优先可避免『套餐费』误命中『餐费』等子串问题。
    """
    best_cat = None
    best_len = 0
    for cat, kws in keyword_map.items():
        for kw in kws:
            if kw and kw in text and len(kw) > best_len:
                best_cat = cat
                best_len = len(kw)
    return best_cat


def classify_invoice(text):
    """结合发票内容 + 开具单位自主分析分类。
    策略：货物名称区域 > 销售方区域 > 全文兜底；同区域内优先匹配更长关键词。
    """
    text = text or ""
    item_area = _extract_item_area(text)
    seller_area = _extract_seller_area(text)

    # 1. 货物名称区域（最具体）
    cat = _best_category(item_area, CONTENT_KEYWORDS)
    if cat:
        return cat

    # 2. 销售方（开具单位）区域
    cat = _best_category(seller_area, SELLER_KEYWORDS)
    if cat:
        return cat

    # 3. 全文兜底（内容关键词）
    cat = _best_category(text, CONTENT_KEYWORDS)
    if cat:
        return cat

    # 4. 全文兜底（开具单位关键词）
    cat = _best_category(text, SELLER_KEYWORDS)
    if cat:
        return cat

    return "其他"


# ==================== 主程序 ====================
class InvoiceProcessor:
    def __init__(self, root):
        self.root = root
        self.root.title("发票小助手 v3.1")
        self.root.geometry("920x760")
        self.root.minsize(760, 640)

        # 状态变量
        self.source_folder = ""
        self.custom_target_folder = ""
        self.files = []            # 待处理文件（绝对路径）
        self.result_queue = queue.Queue()
        self.is_processing = False
        self.output_mode = tk.StringVar(value="by_month_type")
        self.target_folder = ""

        # 样式
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Microsoft YaHei", 10))
        self.style.configure("TLabel", font=("Microsoft YaHei", 10))
        self.style.configure("TLabelframe.Label", font=("Microsoft YaHei", 10, "bold"))

        self._build_ui()
        _set_window_icon(self.root)

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        # 标题
        ttk.Label(main, text="发票小助手 v3.1",
                  font=("Microsoft YaHei", 18, "bold")).pack(pady=(0, 6))

        ttk.Label(main, text="支持 PDF / JPG / PNG / BMP / TIFF / WEBP，自动提取金额、识别类型并归类重命名。",
                  foreground="#555").pack(pady=(0, 10))

        # 输入选择
        in_frame = ttk.LabelFrame(main, text="① 选择发票")
        in_frame.pack(fill=tk.X, pady=4)

        row = ttk.Frame(in_frame)
        row.pack(fill=tk.X, pady=6, padx=8)
        self.file_label = ttk.Label(row, text="未选择任何文件或文件夹", foreground="#888")
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        ttk.Button(row, text="选择文件", command=self.select_files).pack(side=tk.RIGHT, padx=4)
        ttk.Button(row, text="选择文件夹", command=self.select_folder).pack(side=tk.RIGHT, padx=4)

        # 输出选择
        out_frame = ttk.LabelFrame(main, text="② 输出设置")
        out_frame.pack(fill=tk.X, pady=4)

        row2 = ttk.Frame(out_frame)
        row2.pack(fill=tk.X, pady=6, padx=8)
        self.output_folder_label = ttk.Label(row2, text="未选择（默认在源文件夹旁创建「xx_处理结果」）", foreground="#888")
        self.output_folder_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.select_output_button = ttk.Button(row2, text="选择输出文件夹", command=self.select_output_folder)
        self.select_output_button.pack(side=tk.RIGHT, padx=4)

        # 归类方式
        opt_frame = ttk.LabelFrame(main, text="③ 归类方式")
        opt_frame.pack(fill=tk.X, pady=4)

        opt_row = ttk.Frame(opt_frame)
        opt_row.pack(fill=tk.X, pady=8, padx=8)
        modes = [
            ("按月份+类型分类", "by_month_type"),
            ("按月份归类", "by_month"),
            ("按类型分类", "by_type"),
            ("覆盖源文件（原地重命名）", "overwrite"),
        ]
        for text, value in modes:
            ttk.Radiobutton(opt_row, text=text, variable=self.output_mode, value=value).pack(side=tk.LEFT, padx=10)

        # 开始处理
        self.process_button = ttk.Button(main, text="开始处理", command=self.start_processing)
        self.process_button.pack(pady=10)
        self.process_button["state"] = "disabled"

        # 进度
        self.progress_label = ttk.Label(main, text="准备就绪", foreground="#555")
        self.progress_label.pack(anchor=tk.W, pady=(0, 2))
        self.progress_bar = ttk.Progressbar(main, orient=tk.HORIZONTAL, mode="determinate")
        self.progress_bar.pack(fill=tk.X)

        # 结果
        res_frame = ttk.LabelFrame(main, text="处理结果")
        res_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        self.result_text = tk.Text(res_frame, wrap=tk.WORD, height=12, font=("Consolas", 9))
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
        sb = ttk.Scrollbar(res_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=sb.set)

        # 版权信息（全英文）
        ttk.Label(main, text="Copyright (c) 2026 yingxiang.he@zkh.com. All rights reserved.",
                  font=("Arial", 8), foreground="#999").pack(pady=(4, 0))

        self.output_mode.trace_add("write", self._on_mode_change)

    # ---------- 选择 ----------
    def select_folder(self):
        if self.is_processing:
            messagebox.showinfo("提示", "正在处理中，请稍候...")
            return
        path = filedialog.askdirectory(title="选择包含发票的文件夹")
        if not path:
            return
        self.source_folder = path
        self.files = self._scan_folder(path)
        self._refresh_file_label()
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"已选择文件夹: {path}\n")
        self.result_text.insert(tk.END, f"共找到 {len(self.files)} 个可处理的发票文件\n")

    def select_files(self):
        if self.is_processing:
            messagebox.showinfo("提示", "正在处理中，请稍候...")
            return
        paths = filedialog.askopenfilenames(title="选择发票文件", filetypes=FILE_DIALOG_TYPES)
        if not paths:
            return
        self.source_folder = os.path.dirname(paths[0])
        self.files = [p for p in paths if os.path.splitext(p)[1].lower() in SUPPORTED_EXTS]
        self._refresh_file_label()
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"已选择 {len(self.files)} 个发票文件\n")
        self.result_text.insert(tk.END, f"所在文件夹: {self.source_folder}\n")

    def _scan_folder(self, path):
        found = []
        for name in os.listdir(path):
            full = os.path.join(path, name)
            if os.path.isfile(full) and os.path.splitext(name)[1].lower() in SUPPORTED_EXTS:
                found.append(full)
        found.sort()
        return found

    def _refresh_file_label(self):
        if self.files:
            if len(self.files) == 1:
                self.file_label.config(text=os.path.basename(self.files[0]), foreground="#000")
            else:
                self.file_label.config(text=f"已选择 {len(self.files)} 个文件（{self.source_folder}）", foreground="#000")
            self.process_button["state"] = "normal"
        else:
            self.file_label.config(text="未选择任何文件或文件夹", foreground="#888")
            self.process_button["state"] = "disabled"

    def select_output_folder(self):
        path = filedialog.askdirectory(title="选择输出文件夹")
        if path:
            self.custom_target_folder = path
            self.output_folder_label.config(text=path, foreground="#000")

    def _on_mode_change(self, *args):
        if self.output_mode.get() == "overwrite":
            self.select_output_button["state"] = "disabled"
        elif not self.is_processing:
            self.select_output_button["state"] = "normal"

    # ---------- 处理 ----------
    def start_processing(self):
        if not self.files:
            messagebox.showwarning("警告", "请先选择发票文件或文件夹！")
            return
        if self.is_processing:
            return

        if self.output_mode.get() == "overwrite":
            if not messagebox.askyesno(
                    "确认覆盖",
                    "覆盖源文件模式将直接重命名原始文件，此操作不可撤销。\n\n确定要继续吗？"):
                return

        # 确定目标文件夹
        try:
            if self.output_mode.get() == "overwrite":
                self.target_folder = self.source_folder
            else:
                base_name = os.path.basename(self.source_folder.rstrip("\\/"))
                if self.custom_target_folder:
                    self.target_folder = os.path.join(self.custom_target_folder, f"{base_name}_处理结果")
                else:
                    self.target_folder = os.path.join(os.path.dirname(self.source_folder), f"{base_name}_处理结果")
                counter = 1
                original = self.target_folder
                while os.path.exists(self.target_folder):
                    self.target_folder = f"{original}_{counter}"
                    counter += 1
                os.makedirs(self.target_folder, exist_ok=True)
        except Exception as e:
            messagebox.showerror("错误", f"创建输出文件夹失败: {e}")
            return

        # 重置 UI
        self.progress_bar["value"] = 0
        self.progress_bar["maximum"] = len(self.files)
        self.progress_label.config(text="正在处理...（首次使用会加载 OCR 引擎，稍慢）")
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"开始处理，共 {len(self.files)} 个文件\n输出目录: {self.target_folder}\n\n")
        self.process_button["state"] = "disabled"
        self.select_output_button["state"] = "disabled"
        self.is_processing = True

        files_snapshot = list(self.files)
        worker = threading.Thread(target=self._worker, args=(files_snapshot,), daemon=True)
        worker.start()
        self.root.after(100, self._poll)

    def _worker(self, files):
        for f in files:
            result = self.process_single_file(f)
            self.result_queue.put(result)
        self.result_queue.put(None)  # 结束哨兵

    def _poll(self):
        processed = 0
        results = []
        done = False
        while True:
            try:
                item = self.result_queue.get_nowait()
            except queue.Empty:
                break
            if item is None:
                done = True
                break
            processed += 1
            results.append(item)
            self.progress_bar["value"] = processed
            self.progress_label.config(text=f"处理中... {processed}/{self.progress_bar['maximum']}")
            self._render_result(item)

        if done:
            self._finish(results)
        else:
            self.root.after(100, self._poll)

    def _render_result(self, item):
        fname, amount, category, date_str, new_filename, error = item
        if amount:
            self.result_text.insert(tk.END, f"✓ {fname}  →  {new_filename}\n")
        else:
            self.result_text.insert(tk.END, f"✗ {fname}: {error}\n")
        self.result_text.see(tk.END)

    def _finish(self, results):
        self.generate_report(results)
        success = sum(1 for r in results if r[1])
        self.progress_label.config(text=f"处理完成！成功 {success} 个，失败 {len(results) - success} 个")
        self.process_button["state"] = "normal"
        self.select_output_button["state"] = "normal" if self.output_mode.get() != "overwrite" else "disabled"
        self.is_processing = False
        self.custom_target_folder = ""
        self.output_folder_label.config(
            text="未选择（默认在源文件夹旁创建「xx_处理结果」）", foreground="#888")
        messagebox.showinfo(
            "处理完成",
            f"共处理 {len(results)} 个文件\n成功 {success} 个，失败 {len(results) - success} 个\n\n结果保存在:\n{self.target_folder}")

    # ---------- 单文件处理 ----------
    def process_single_file(self, filepath):
        fname = os.path.basename(filepath)
        try:
            ext = os.path.splitext(filepath)[1].lower()
            if not os.path.exists(filepath):
                return (fname, None, None, None, None, "文件不存在")

            # 提取文本
            if ext in PDF_EXTS:
                text = extract_text_from_pdf(filepath)
            elif ext in IMAGE_EXTS:
                text = extract_text_from_image(filepath)
            else:
                return (fname, None, None, None, None, f"不支持的文件格式: {ext}")

            if not text or not text.strip():
                return (fname, None, None, None, None, "无法识别内容（可能为扫描件或清晰度不足）")

            amount = extract_amount(text)
            if not amount:
                return (fname, None, None, None, None, "未识别到价税合计金额")

            date_str = extract_invoice_date(text, file_path=filepath)
            category = classify_invoice(text)

            # 命名：2026年8月-交通类-820.00元.ext
            new_filename = f"{date_str}-{category}-{amount}元{ext}"
            mode = self.output_mode.get()

            if mode == "overwrite":
                target_dir = self.source_folder
                target_path = self._unique_path(target_dir, new_filename, filepath)
                os.rename(filepath, target_path)
            else:
                if mode == "by_month":
                    sub = os.path.join(self.target_folder, date_str)
                elif mode == "by_type":
                    sub = os.path.join(self.target_folder, category)
                elif mode == "by_month_type":
                    sub = os.path.join(self.target_folder, date_str, category)
                else:
                    sub = self.target_folder
                os.makedirs(sub, exist_ok=True)
                target_path = self._unique_path(sub, new_filename)
                shutil.copy2(filepath, target_path)

            return (fname, amount, category, date_str, new_filename, None)

        except Exception as e:
            print(f"处理 {fname} 出错:")
            traceback.print_exc()
            return (fname, None, None, None, None, f"处理错误: {e}")

    def _unique_path(self, directory, filename, exclude_path=None):
        """返回不冲突的目标路径（重名自动加 _1、_2 后缀）。"""
        target = os.path.join(directory, filename)
        if exclude_path and os.path.normcase(target) == os.path.normcase(exclude_path):
            return target
        if not os.path.exists(target):
            return target
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(directory, f"{base}_{counter}{ext}")):
            counter += 1
        return os.path.join(directory, f"{base}_{counter}{ext}")

    # ---------- 报告 ----------
    def generate_report(self, results):
        report_dir = self.source_folder if self.output_mode.get() == "overwrite" else self.target_folder
        report_path = os.path.join(report_dir, "处理报告.txt")
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("发票处理报告\n=============\n\n")
                f.write(f"源文件夹: {self.source_folder}\n")
                f.write(f"目标文件夹: {self.target_folder}\n")
                f.write(f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("处理明细:\n---------\n\n")

                success = 0
                fail = 0
                stats = {}
                for fname, amount, category, date_str, new_filename, error in results:
                    if amount:
                        success += 1
                        f.write(f"✓ {fname} -> {new_filename}（{category}，{amount}元）\n")
                        stats.setdefault(category, {"count": 0, "total": 0.0})
                        stats[category]["count"] += 1
                        try:
                            stats[category]["total"] += float(amount)
                        except ValueError:
                            pass
                    else:
                        fail += 1
                        f.write(f"✗ {fname}: {error}\n")

                if stats:
                    f.write("\n分类统计:\n---------\n")
                    for cat, s in stats.items():
                        f.write(f"{cat}: {s['count']} 笔，合计 {s['total']:,.2f} 元\n")

                f.write("\n统计信息:\n---------\n")
                f.write(f"总文件数: {len(results)}\n")
                f.write(f"成功: {success}\n")
                f.write(f"失败: {fail}\n")
        except Exception as e:
            print(f"生成报告失败: {e}")


def _run_selftest():
    """内置自检：生成测试图片 -> OCR -> 提取金额/日期/分类 -> 写入结果文件。
    供开发者/用户诊断 OCR 是否可用（命令行：InvoiceSorter.exe --selftest）。
    """
    import sys
    result_path = os.path.join(os.path.dirname(sys.executable), "selftest_result.txt")
    lines = ["发票小助手 自检", "================="]
    ok = False
    try:
        from PIL import Image, ImageDraw, ImageFont
        font_path = None
        for cand in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf",
                     "C:/Windows/Fonts/simsun.ttc"):
            if os.path.exists(cand):
                font_path = cand
                break
        img = Image.new("RGB", (1200, 560), "white")
        d = ImageDraw.Draw(img)
        font = ImageFont.truetype(font_path, 36)
        d.text((80, 90), "销售方信息 名称：滴滴出行科技有限公司", font=font, fill="black")
        d.text((80, 170), "项目名称：*运输服务*客运服务费", font=font, fill="black")
        d.text((80, 250), "价税合计（小写）￥820.00", font=font, fill="black")
        d.text((80, 330), "开票日期：2026年08月03日", font=font, fill="black")
        tmp = os.path.join(tempfile.gettempdir(), "_invoice_selftest.png")
        img.save(tmp)

        text = extract_text_from_image(tmp)
        amount = extract_amount(text)
        date_str = extract_invoice_date(text)
        category = classify_invoice(text)

        lines.append(f"OCR文本: {text!r}")
        lines.append(f"金额={amount}  日期={date_str}  分类={category}")
        ok = (amount == "820.00" and category == "交通类")
        try:
            os.remove(tmp)
        except OSError:
            pass
    except Exception:
        lines.append(traceback.format_exc())

    lines.append("结论: " + ("通过 PASS" if ok else "失败 FAIL"))
    try:
        with open(result_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except OSError:
        pass
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        # 内置自检：验证 OCR 引擎与识别链路，结果写入 exe 同目录 selftest_result.txt
        _run_selftest()
    root = tk.Tk()
    app = InvoiceProcessor(root)
    root.mainloop()
