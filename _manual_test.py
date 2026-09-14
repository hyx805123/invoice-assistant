# -*- coding: utf-8 -*-
"""发票小助手 v3.1 手动验收测试脚本（不依赖 GUI 交互）。"""

import os
import sys
import shutil
import tempfile
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import invoice_processor as m


def test_amount_extraction():
    print("\n[金额提取测试]")
    cases = [
        ("价税合计（大写）捌佰贰拾元整 （小写）￥820.00", "820.00"),
        ("价税合计（大写）壹佰贰拾叁元肆角伍分（小写）¥123.45", "123.45"),
        ("[小写] ¥ 1,234.56 元", "1234.56"),
        ("价税合计：￥99.00", "99.00"),
        ("总计：¥0.00", None),  # 0 过滤
        ("税率 13%", None),
        ("人民币：￥８２０．００", "820.00"),  # 全角
    ]
    ok = 0
    for text, expected in cases:
        got = m.extract_amount(text)
        status = "PASS" if got == expected else "FAIL"
        if got == expected:
            ok += 1
        print(f"  {status}: 期望={expected}, 实际={got}")
    print(f"  结果: {ok}/{len(cases)} 通过")
    return ok == len(cases)


def test_date_extraction():
    print("\n[日期提取测试]")
    cases = [
        ("开票日期：2026年08月03日", "2026年8月"),
        ("开票日期：2026-07-15", "2026年7月"),
        ("开票日期：2026/06/01", "2026年6月"),
        ("2026.05.01", "2026年5月"),
        ("20260501", "2026年5月"),
    ]
    ok = 0
    for text, expected in cases:
        got = m.extract_invoice_date(text)
        status = "PASS" if got == expected else "FAIL"
        if got == expected:
            ok += 1
        print(f"  {status}: 期望={expected}, 实际={got}")
    print(f"  结果: {ok}/{len(cases)} 通过")
    return ok == len(cases)


def test_classification():
    print("\n[分类测试]")
    cases = [
        ("销售方：滴滴出行，项目：客运服务费", "交通类"),
        ("销售方：美团，项目：餐饮服务餐费", "餐饮类"),
        ("销售方：中国移动，项目：套餐费", "通讯类"),
        ("销售方：顺丰，项目：运输费", "物流类"),
        ("销售方：京东，项目：电脑配件", "办公类"),
        ("销售方：如家酒店，项目：住宿服务房费", "住宿类"),
        ("销售方：某医院，项目：诊疗费", "医疗类"),
        ("销售方：某水务公司，项目：水费", "水电类"),
        ("销售方：某培训机构，项目：培训课程", "教育培训类"),
        ("销售方：某广告公司，项目：广告设计", "广告宣传类"),
        ("销售方：某咨询公司，项目：服务费", "服务类"),
        ("销售方：某某公司，项目：未知事项", "其他"),
    ]
    ok = 0
    for text, expected in cases:
        got = m.classify_invoice(text)
        status = "PASS" if got == expected else "FAIL"
        if got == expected:
            ok += 1
        print(f"  {status}: 期望={expected}, 实际={got}")
    print(f"  结果: {ok}/{len(cases)} 通过")
    return ok == len(cases)


def test_end_to_end():
    """端到端：生成图片 -> 走 InvoiceProcessor.process_single_file -> 验证输出与报告。"""
    print("\n[端到端流程测试]")
    from PIL import Image, ImageDraw, ImageFont
    font_path = "C:/Windows/Fonts/msyh.ttc"
    if not os.path.exists(font_path):
        print("  SKIP: 未找到中文字体")
        return True
    font = ImageFont.truetype(font_path, 32)

    tmpdir = tempfile.mkdtemp(prefix="invoice_test_")
    root = None
    try:
        src = os.path.join(tmpdir, "source")
        out = os.path.join(tmpdir, "output")
        os.makedirs(src)
        os.makedirs(out)

        def make_invoice(path, seller, item, amount, date):
            img = Image.new("RGB", (1200, 500), "white")
            d = ImageDraw.Draw(img)
            d.text((80, 80), f"销售方信息 名称：{seller}", font=font, fill="black")
            d.text((80, 160), f"项目名称：{item}", font=font, fill="black")
            d.text((80, 240), f"价税合计（小写）￥{amount}", font=font, fill="black")
            d.text((80, 320), f"开票日期：{date}", font=font, fill="black")
            img.save(path)

        make_invoice(os.path.join(src, "a.png"), "滴滴出行科技有限公司", "*运输服务*客运服务费", "820.00", "2026年08月03日")
        make_invoice(os.path.join(src, "b.png"), "美团科技有限公司", "*餐饮服务*餐费", "123.45", "2026年07月15日")
        make_invoice(os.path.join(src, "c.png"), "中国移动有限公司", "*电信服务*套餐费", "88.00", "2026年09月01日")

        root = tk.Tk()
        root.withdraw()
        app = m.InvoiceProcessor(root)
        app.source_folder = src
        app.target_folder = out
        app.output_mode = tk.StringVar(value="by_month_type")
        app.custom_target_folder = ""
        app.files = []
        app.is_processing = False

        files = app._scan_folder(src)
        assert len(files) == 3, f"应扫描到 3 个文件，实际 {len(files)}"
        print(f"  扫描到 {len(files)} 个文件")

        results = []
        for f in files:
            r = app.process_single_file(f)
            results.append(r)
            fname, amount, category, date_str, new_filename, error = r
            print(f"  {fname}: 金额={amount} 分类={category} 日期={date_str} 新名={new_filename} 错误={error}")
            assert error is None, f"处理失败: {error}"
            assert amount is not None, "未识别金额"
            assert category not in (None, ""), "分类为空"

        # 验证输出目录结构
        for d in ["2026年8月", "2026年7月", "2026年9月"]:
            assert os.path.isdir(os.path.join(out, d)), f"缺少目录 {d}"
        assert os.path.isdir(os.path.join(out, "2026年8月", "交通类"))
        assert os.path.isdir(os.path.join(out, "2026年7月", "餐饮类"))
        assert os.path.isdir(os.path.join(out, "2026年9月", "通讯类"))
        print("  输出目录结构正确")

        # 生成处理报告
        app.generate_report(results)
        report_path = os.path.join(out, "处理报告.txt")
        assert os.path.isfile(report_path), "缺少处理报告"
        with open(report_path, encoding="utf-8") as f:
            content = f.read()
        assert "交通类" in content and "餐饮类" in content and "通讯类" in content
        assert "820.00" in content and "123.45" in content
        print(f"  处理报告生成正常（{len(content)} 字符）")
        return True
    finally:
        try:
            if root is not None:
                root.destroy()
        except Exception:
            pass
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_ui_code_review():
    print("\n[UI/前端代码审查]")
    src = open("invoice_processor.py", encoding="utf-8").read()
    checks = [
        ("窗口标题为中文", "发票小助手 v3.1" in src),
        ("设置窗口图标", "_set_window_icon" in src),
        ("iconbitmap 加载 logo.ico", 'root.iconbitmap(ico)' in src),
        ("iconphoto 加载 logo.png", 'root.iconphoto' in src),
        ("版权信息", "yingxiang.he@zkh.com" in src),
        ("未选择文件防护", "请先选择发票文件或文件夹" in src),
        ("覆盖源文件确认", "此操作不可撤销" in src),
        ("进度条", "progress_bar" in src),
        ("结果区", "result_text" in src),
        ("多选/单选输出模式", "by_month_type" in src and "overwrite" in src),
    ]
    all_ok = True
    for name, passed in checks:
        print(f"  {'PASS' if passed else 'FAIL'}: {name}")
        if not passed:
            all_ok = False
    return all_ok


def test_distribution():
    print("\n[交付物检查]")
    checks = [
        ("dist/InvoiceSorter.exe（v3.0）", os.path.isfile("dist/InvoiceSorter.exe")),
        ("dist/发票小助手-v3.1.exe（v3.1）", os.path.isfile("dist/发票小助手-v3.1.exe")),
        ("logo.ico", os.path.isfile("logo.ico")),
        ("发票小助手-v3.1.spec", os.path.isfile("发票小助手-v3.1.spec")),
        ("README.md", os.path.isfile("README.md")),
        ("使用说明.txt", os.path.isfile("使用说明.txt")),
        ("overview.md", os.path.isfile("overview.md")),
        ("requirements.txt", os.path.isfile("requirements.txt")),
        ("build.bat", os.path.isfile("build.bat")),
    ]
    for name, exists in checks:
        print(f"  {'OK' if exists else 'MISSING'}: {name}")
    return all(e for _, e in checks)


if __name__ == "__main__":
    print("=" * 50)
    print("发票小助手 v3.1 验收测试")
    print("=" * 50)
    results = [
        ("金额提取", test_amount_extraction()),
        ("日期提取", test_date_extraction()),
        ("分类", test_classification()),
        ("端到端", test_end_to_end()),
        ("UI/前端", test_ui_code_review()),
        ("交付物", test_distribution()),
    ]
    print("\n" + "=" * 50)
    print("汇总")
    print("=" * 50)
    overall = True
    for name, ok in results:
        print(f"  {name:　<6s}: {'通过' if ok else '失败'}")
        if not ok:
            overall = False
    print(f"\n总结果: {'全部通过 ✓' if overall else '存在失败 ✗'}")
    sys.exit(0 if overall else 1)
