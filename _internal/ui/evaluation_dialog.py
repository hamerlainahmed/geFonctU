# -*- coding: utf-8 -*-
"""
evaluation_dialog.py — منطق حساب النقطة الإدارية + مولّد HTML للاستمارة

يحتوي على:
  - دوال المنطق الرياضي لسلّم التنقيط
  - EvaluationPrinter: مولّد HTML لاستمارة التنقيط الفردية
  - دوال مساعدة للطباعة الجماعية
"""

import database as db

# ---------------------------------------------------------------------------
# ┌─ المنطق الرياضي لسلّم التنقيط ─────────────────────────────────────────┐
# │  base_min  = 9.0 + (degree - 1) * 0.5                                   │
# │  max_limit = base_min + 4.5                                              │
# │  الخطوة    = 0.5                                                         │
# └──────────────────────────────────────────────────────────────────────────┘


def compute_score_limits(degree: int):
    """إرجاع (min_score, max_score) بناءً على الدرجة."""
    base_min = 9.0 + (degree - 1) * 0.5
    max_limit = base_min + 4.5
    return round(base_min, 1), round(max_limit, 1)


def get_remark(score: float, base_min: float) -> str:
    """
    تحديد الملاحظة (النعت) بناءً على الفارق بين النقطة الممنوحة والحد الأدنى.

    الفارق   | الملاحظة
    0 → 0.5  | دون الوسط
    1.0 → 1.5| متوسط
    2.0 → 2.5| جيد
    3.0 → 3.5| جيد جداً
    4.0 → 4.5| ممتاز
    """
    diff = round(score - base_min, 2)
    if diff < 0:
        return "خارج السلم"
    elif diff <= 0.5:
        return "دون الوسط"
    elif diff <= 1.5:
        return "متوسط"
    elif diff <= 2.5:
        return "جيد"
    elif diff <= 3.5:
        return "جيد جداً"
    else:
        return "ممتاز"


def score_to_arabic_words(score: float) -> str:
    """تحويل النقطة (0.0 – 20.0 بخطوة 0.5) إلى كلمات بالعربية."""
    whole = int(score)
    half = abs(score - whole) >= 0.4  # True إذا كان 0.5

    ones = [
        "", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة",
        "ستة", "سبعة", "ثمانية", "تسعة", "عشرة",
        "أحد عشر", "اثنا عشر", "ثلاثة عشر", "أربعة عشر", "خمسة عشر",
        "ستة عشر", "سبعة عشر", "ثمانية عشر", "تسعة عشر", "عشرون",
    ]

    if whole == 0 and half:
        return "نصف"
    if whole == 0:
        return "صفر"

    base = ones[whole] if whole < len(ones) else str(whole)
    if half:
        return base + " وَنِصف"
    return base


# ---------------------------------------------------------------------------
# ┌─ دوال مساعدة ──────────────────────────────────────────────────────────┐
# └──────────────────────────────────────────────────────────────────────────┘

def get_previous_years(current_year_str: str, count: int = 3) -> list:
    """
    حساب السنوات الثلاث السابقة للسنة الدراسية الحالية.
    مثال: "2025/2026" → ["2022/2023", "2023/2024", "2024/2025"]
    """
    try:
        start_yr = int(current_year_str.split("/")[0])
    except (ValueError, IndexError):
        start_yr = 2025

    years = []
    for i in range(count, 0, -1):
        y1 = start_yr - i
        y2 = y1 + 1
        years.append(f"{y1}/{y2}")
    return years


WORKER_GRADES = ["عامل مهني", "عون وقاية", "عون خدمة", "سائق", "طباخ", "مخزني", "حاجب"]


def is_eligible_for_evaluation(employee) -> bool:
    """
    هل الموظف خاضع للتنقيط؟
    المعفون: الرتب العمّالية + أصحاب الدرجة 0.
    """
    emp = dict(employee) if not isinstance(employee, dict) else employee
    grade = emp.get("grade") or ""
    degree_str = emp.get("degree") or ""

    # رتبة عمّالية → معفى
    if any(w in grade for w in WORKER_GRADES):
        return False

    # درجة 0 أو فارغة → معفى
    try:
        degree_val = int(degree_str)
        if degree_val == 0:
            return False
    except (ValueError, TypeError):
        # درجة فارغة أو غير رقمية → معفى
        if not degree_str.strip():
            return False

    return True


def get_eligible_employees():
    """إرجاع قائمة الموظفين الخاضعين للتقييم."""
    all_emps = db.get_all_employees()
    return [e for e in all_emps if is_eligible_for_evaluation(e)]


# ---------------------------------------------------------------------------
# ┌─ مولّد HTML لاستمارة التنقيط الفردية ─────────────────────────────────┐
# └──────────────────────────────────────────────────────────────────────────┘

class EvaluationPrinter:
    """يولّد HTML كاملاً لاستمارة التنقيط الفردية (RTL) جاهزاً للطباعة."""

    @staticmethod
    def _val(v, fallback="/"):
        """عرض القيمة أو / إذا فارغة."""
        if v is None:
            return fallback
        s = str(v).strip()
        if s == "" or s == "0" or s == "0.0":
            return fallback
        return s

    @staticmethod
    def _date_val(v, fallback="/"):
        """عرض التاريخ أو / إذا فارغ."""
        if not v or not str(v).strip():
            return fallback
        return str(v).strip().replace("-", "/")

    @staticmethod
    def generate_html(employee: dict, evals: list, settings: dict,
                      current_score=None, current_year: str = "",
                      current_remark: str = "") -> str:

        from ui.print_header import _get_school_initials
        from datetime import datetime

        school   = settings.get("school_name", "المؤسسة التعليمية")
        wilaya   = settings.get("wilaya", "")
        address  = settings.get("school_address", "")
        sy       = settings.get("school_year", "2025/2026")
        initials = _get_school_initials(school)
        year_now = datetime.now().year
        doc_date = datetime.now().strftime("%Y-%m-%d")

        if not current_year:
            current_year = sy

        school_display = school
        if address:
            school_display += f" - {address}"

        emp = employee if isinstance(employee, dict) else dict(employee)
        emp_ln       = emp.get("last_name", "")
        emp_fn       = emp.get("first_name", "")
        emp_maiden   = emp.get("maiden_name") or ""
        emp_bd       = EvaluationPrinter._date_val(emp.get("birth_date"))
        emp_bp       = emp.get("birth_place") or ""
        emp_family   = emp.get("family_status") or ""
        emp_diploma  = emp.get("diploma") or ""
        emp_dip_date = EvaluationPrinter._date_val(emp.get("diploma_date"))
        emp_grade    = emp.get("grade") or ""
        emp_subject  = emp.get("subject") or ""
        emp_category = emp.get("category") or ""
        emp_degree   = emp.get("degree") or ""
        eff_date     = EvaluationPrinter._date_val(emp.get("effective_date"))

        birth_str = emp_bd
        if emp_bp:
            birth_str = f"{emp_bd}  بـ {emp_bp}"

        try:
            deg_int = max(1, int(emp_degree))
        except (ValueError, TypeError):
            deg_int = 1
        base_min, _ = compute_score_limits(deg_int)

        # النقطة الحالية للطباعة
        if current_score is not None and current_score > 0:
            score_display = str(current_score)
            score_words = score_to_arabic_words(current_score)
            if not current_remark:
                current_remark = get_remark(current_score, base_min)
        else:
            score_display = "/"
            score_words = ""
            current_remark = ""

        # بناء صفوف جدول السنوات الثلاث
        prev_years = get_previous_years(current_year, 3)
        evals_dict = {}
        if evals:
            for ev in evals:
                ev_dict = dict(ev) if not isinstance(ev, dict) else ev
                evals_dict[ev_dict["school_year"]] = ev_dict

        _v = EvaluationPrinter._val
        _d = EvaluationPrinter._date_val

        table_rows = ""
        for i, yr in enumerate(prev_years):
            ev = evals_dict.get(yr)
            if ev:
                edu_s  = _v(ev.get("edu_score"))
                edu_dt = _d(ev.get("edu_date"))
                adm_s  = _v(ev.get("admin_score"))
                adm_dt = _d(ev.get("eval_date"))
            else:
                edu_s = edu_dt = adm_s = adm_dt = "/"

            table_rows += f"""
            <tr>
                <td style="text-align:center; font-weight:bold; background:#f1f5f9;">{i+1}</td>
                <td style="text-align:center; font-weight:bold; background:#e8f0fe;">{yr}</td>
                <td style="text-align:center;">{edu_s}</td>
                <td style="text-align:center;">{edu_dt}</td>
                <td style="text-align:center;">{adm_s}</td>
                <td style="text-align:center;">{adm_dt}</td>
            </tr>"""

        score_line = ""
        if score_words:
            score_line = f"{score_words}  ({score_display})  — {current_remark}"
        else:
            score_line = "/"

        html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<style>
  body {{
    font-family: 'Amiri', 'Traditional Arabic', 'Arial', sans-serif;
    font-size: 12pt;
    direction: rtl;
    margin: 0;
    padding: 0;
    color: #000;
    line-height: 1.3;
  }}
  h2 {{
    text-align: center;
    border: 4px solid #000;
    padding: 10px 20px;
    display: inline-block;
    margin: 10px auto;
    font-size: 18pt;
    font-weight: bold;
  }}
  .center-block {{ text-align: center; margin-bottom: 10px; }}
  table.main-table {{
    width: 96%;
    border-collapse: collapse;
    margin: 10px auto;
  }}
  table.main-table th, table.main-table td {{
    border: 1px solid #000;
    padding: 5px 4px;
    font-size: 11pt;
    text-align: center;
  }}
  table.main-table th {{
    background: #e0e0e0;
    font-weight: bold;
  }}
  .dotted-line {{
    border: none;
    border-bottom: 1px dotted #555;
    width: 100%;
    margin: 5px 0;
  }}
  .footer-table {{
    width: 96%;
    margin: 12px auto 0;
    border-collapse: collapse;
  }}
  .footer-table td {{
    border: none;
    font-size: 13pt;
    font-weight: bold;
    text-align: center;
    padding: 4px;
  }}
</style>
</head>
<body>

<!-- رأس الصفحة -->
<table width="100%" style="margin-bottom:6px; font-size:12pt; font-weight:bold;">
  <tr><td style="text-align:center;">
    الجمهورية الجزائرية الديمقراطية الشعبية<br/>وزارة التربية الوطنية
  </td></tr>
</table>

<table width="100%" style="font-size:11pt; font-weight:bold; margin-bottom:4px;">
  <tr>
    <td style="text-align:right; width:55%;">
      مديرية التربية لولاية {wilaya}<br/>{school_display}
    </td>
    <td style="text-align:left; width:45%;">
      حرر في : {doc_date}<br/>الرقم: ............/ل.م.ن.ق/{year_now}
    </td>
  </tr>
</table>

<div class="center-block">
  <h2>استمارة التنقيط الفردية<br/>الموسم الدراسي {current_year}</h2>
</div>

<!-- بيانات الموظف -->
<table width="96%" style="font-size:12pt; border-collapse:collapse; margin: 8px auto;">
  <tr><td width="30%" style="font-weight:bold; text-align:right; padding:3px 6px;">اللقب :</td>
      <td style="border-bottom:1px solid #555; padding:3px 6px;">{emp_ln}</td></tr>
  <tr><td style="font-weight:bold; text-align:right; padding:3px 6px;">الإسم :</td>
      <td style="border-bottom:1px solid #555; padding:3px 6px;">{emp_fn}</td></tr>
  <tr><td style="font-weight:bold; text-align:right; padding:3px 6px;">اللقب الأصلي للمتزوجات :</td>
      <td style="border-bottom:1px solid #555; padding:3px 6px;">{emp_maiden}</td></tr>
  <tr><td style="font-weight:bold; text-align:right; padding:3px 6px;">تاريخ ومكان الميلاد :</td>
      <td style="border-bottom:1px solid #555; padding:3px 6px;">{birth_str}</td></tr>
  <tr><td style="font-weight:bold; text-align:right; padding:3px 6px;">الحالة العائلية :</td>
      <td style="border-bottom:1px solid #555; padding:3px 6px;">{emp_family}</td></tr>
  <tr><td style="font-weight:bold; text-align:right; padding:3px 6px;">الشهادة المحصل عليها :</td>
      <td style="border-bottom:1px solid #555; padding:3px 6px;">{emp_diploma}</td></tr>
  <tr><td style="font-weight:bold; text-align:right; padding:3px 6px;">تاريخ الحصول عليها :</td>
      <td style="border-bottom:1px solid #555; padding:3px 6px;">{emp_dip_date}</td></tr>
  <tr><td style="font-weight:bold; text-align:right; padding:3px 6px;">الرتبة الحالية :</td>
      <td style="border-bottom:1px solid #555; padding:3px 6px;">{emp_grade}</td></tr>
  <tr><td style="font-weight:bold; text-align:right; padding:3px 6px;">المادة :</td>
      <td style="border-bottom:1px solid #555; padding:3px 6px;">{emp_subject}</td></tr>
  <tr><td style="font-weight:bold; text-align:right; padding:3px 6px;">الصنف :</td>
      <td style="border-bottom:1px solid #555; padding:3px 6px;">{emp_category}</td></tr>
  <tr><td style="font-weight:bold; text-align:right; padding:3px 6px;">الدرجة :</td>
      <td style="border-bottom:1px solid #555; padding:3px 6px;">{emp_degree}</td></tr>
  <tr><td style="font-weight:bold; text-align:right; padding:3px 6px;">تاريخ سريان الدرجة :</td>
      <td style="border-bottom:1px solid #555; padding:3px 6px;">{eff_date}</td></tr>
</table>

<!-- جدول النقاط -->
<p style="font-weight:bold; font-size:12pt; text-align:right; margin: 6px 2%;">
  النقاط المتحصل عليها خلال ثلاث سنوات السابقة
</p>

<table class="main-table">
  <tr>
    <th rowspan="2" style="width:5%;">&nbsp;</th>
    <th rowspan="2" style="width:18%;">السنة الدراسية</th>
    <th colspan="2" style="background:#c8e6c9;">النقطة التربوية</th>
    <th colspan="2" style="background:#bbdefb;">النقطة الإدارية</th>
  </tr>
  <tr>
    <th style="background:#e8f5e9;">النقطة</th>
    <th style="background:#e8f5e9;">تاريخها</th>
    <th style="background:#e3f2fd;">النقطة</th>
    <th style="background:#e3f2fd;">تاريخها</th>
  </tr>
  {table_rows}
</table>

<!-- النقطة الممنوحة -->
<table width="96%" style="margin: 10px auto; font-size:12pt; border-collapse:collapse;">
  <tr>
    <td style="font-weight:bold; text-align:right; padding: 4px 6px; width:45%;">
      النقطة الإدارية الممنوحة (بالحروف)
    </td>
    <td style="border-bottom: 2px solid #000; padding: 4px 10px; font-weight:bold; font-size:13pt;">
      {score_line}
    </td>
  </tr>
</table>

<!-- ملاحظات المسؤول المباشر -->
<div style="margin: 8px 2%; font-size:12pt;">
  <p style="font-weight:bold; margin-bottom: 4px;">ملاحظات المسؤول المباشر :</p>
  <div class="dotted-line"></div>
  <div class="dotted-line"></div>
</div>

<!-- ملاحظة قانونية -->
<div style="margin: 10px 2%;">
  <p style="font-size:11pt; text-align:center; font-weight:bold;">
    ملاحظة : يجب التقيد بسلم التنقيط الخاص بمطابقة النقطة الإدارية مع الدرجة
  </p>
</div>

<!-- التوقيعات -->
<table class="footer-table">
  <tr>
    <td style="width:50%; text-align:right; padding: 8px 20px;">توقيع الموظف</td>
    <td style="width:50%; text-align:left; padding: 8px 20px;">مدير المؤسسة</td>
  </tr>
  <tr><td colspan="2" style="height:50px;"></td></tr>
</table>

</body>
</html>"""
        return html

    @staticmethod
    def generate_batch_html(employees: list, settings: dict) -> str:
        """
        توليد HTML واحد يحتوي استمارات كل الموظفين المؤهلين.
        يُستعمل page-break-before بين كل استمارة.
        """
        current_year = settings.get("school_year", "2025/2026")
        pages = []

        for emp in employees:
            emp_dict = dict(emp) if not isinstance(emp, dict) else emp
            emp_id = emp_dict["id"]
            evals = db.get_evaluations_for_employee(emp_id)

            # البحث عن النقطة الإدارية الحالية
            current_eval = None
            for ev in evals:
                ev_d = dict(ev) if not isinstance(ev, dict) else ev
                if ev_d["school_year"] == current_year:
                    current_eval = ev_d
                    break

            if current_eval:
                cur_score = current_eval.get("admin_score")
                cur_remark = current_eval.get("remark") or ""
                if cur_score and float(cur_score) > 0:
                    cur_score = float(cur_score)
                else:
                    cur_score = None
                    cur_remark = ""
            else:
                cur_score = None
                cur_remark = ""

            html = EvaluationPrinter.generate_html(
                employee=emp_dict,
                evals=evals,
                settings=settings,
                current_score=cur_score,
                current_year=current_year,
                current_remark=cur_remark,
            )
            pages.append(html)

        if not pages:
            return "<html><body><p>لا يوجد موظفون مؤهلون للتقييم.</p></body></html>"

        # دمج الصفحات مع فاصل صفحات CSS
        # نستخرج محتوى <body> من كل صفحة ونجمعها
        import re
        combined_bodies = []
        for i, page_html in enumerate(pages):
            match = re.search(r'<body[^>]*>(.*?)</body>', page_html, re.DOTALL)
            if match:
                body_content = match.group(1)
            else:
                body_content = page_html

            if i > 0:
                combined_bodies.append(
                    '<div style="page-break-before: always;"></div>'
                )
            combined_bodies.append(body_content)

        # نستخرج <style> من الصفحة الأولى
        style_match = re.search(r'<style>(.*?)</style>', pages[0], re.DOTALL)
        style_content = style_match.group(1) if style_match else ""

        final_html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<style>{style_content}</style>
</head>
<body>
{"".join(combined_bodies)}
</body>
</html>"""
        return final_html
