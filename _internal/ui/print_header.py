# -*- coding: utf-8 -*-
"""
Print Header Helper — Generates standardized RTL Arabic document headers
with institution code support for all printable documents.
"""

import database as db


def get_document_header(settings=None, doc_number="", show_number=True):
    """
    Generate a standardized document header with institution code.
    
    Args:
        settings: dict of settings (if None, will be fetched from DB)
        doc_number: Document number to display
        show_number: Whether to show the document number
    
    Returns:
        HTML string for the header
    """
      # Generate school initials for ref number
        school_initials = self._get_school_initials(school)

    if settings is None:
        settings = db.get_all_settings()
    
    school = settings.get("school_name", "المؤسسة التعليمية")
    school_code = settings.get("school_code", "")
    wilaya = settings.get("wilaya", "")
    year = QDate.currentDate().year()
    school_code_html = ""
    if school_code:
        school_code_html = f"<br/>رمز المؤسسة: {school_code}"
    
    number_section = ""
    if show_number and doc_number:
        number_section = f"الرقم: {doc_number}"
    
    header = f"""
    <div style="text-align:center; margin-bottom: 20px; font-weight: bold;">
        <div style="font-size:16px;">الجمهورية الجزائرية الديمقراطية الشعبية</div>
        <div style="font-size:16px; text-decoration: underline;">وزارة التربية الوطنية</div>
    </div>
    <table width="100%" style="margin-bottom:20px; font-weight: bold; font-size: 14px;" dir="rtl">
        <tr>
            <td style="text-align:right; width:50%;">
                مديرية التربية لولاية {wilaya}<br/>{school}{school_code_html}
            </td>
            <td style="text-align:left; width:50%;">
                <span style="unicode-bidi: bidi-override; direction: rtl;">الرقم:.............&rlm;/&rlm; %(school_initials)s&rlm;/&rlm; %(year)s</span>
                   
            </td>
        </tr>
    </table>
    """
    return header


def get_document_header_compact(settings=None):
    """
    Generate a compact header for documents like absence reports.
    Includes the institution code.
    """
    if settings is None:
        settings = db.get_all_settings()
    
    school = settings.get("school_name", "المؤسسة التعليمية")
    school_code = settings.get("school_code", "")
    wilaya = settings.get("wilaya", "")
    school_year = settings.get("school_year", "2025/2026")
    
    school_code_html = ""
    if school_code:
        school_code_html = f"<br/>رمز المؤسسة: {school_code}"
    
    header = f"""
    <div style="text-align:center; margin-bottom: 10px; font-weight: bold;">
        <div style="font-size:13px;">الجمهورية الجزائرية الديمقراطية الشعبية</div>
        <div style="font-size:13px; text-decoration: underline;">وزارة التربية الوطنية</div>
    </div>
    <table width="100%" style="margin-bottom:10px; font-weight: bold; font-size: 12px;" dir="rtl">
        <tr>
            <td style="text-align:right; width:50%;">
                مديرية التربية لولاية {wilaya}<br/>{school}{school_code_html}
            </td>
            <td style="text-align:left; width:50%;">
                السنة الدراسية: {school_year}
            </td>
        </tr>
    </table>
    """
    return header
 def _get_school_initials(self, school_name):
        """Extract initials from school name, ignoring honorary/type prefixes.
        E.g. 'متوسطة الشهيد نذار قدور' → 'م.ن.ق'
        The first letter of the school type (متوسطة/ثانوية/ابتدائية) is kept,
        then honorary words are skipped, and initials of remaining words are taken.
        """
        if not school_name:
            return ""

        # Words to skip entirely (honorary titles)
        skip_words = {
            "الشهيد", "الشهيدة", "المجاهد", "المجاهدة", "العلامة",
            "القائد", "الأمير", "الشيخ", "الإمام", "الرئيس",
            "البطل", "العقيد", "الرائد", "المقاوم", "المناضل",
            "شهيد", "مجاهد", "علامة", "قائد", "أمير", "شيخ",
        }

        # School type words — take first letter then skip
        type_words = {
            "متوسطة", "ثانوية", "ابتدائية", "مدرسة", "ليسي",
            "إكمالية", "تقنية",
        }

        words = school_name.strip().split()
        initials = []

        for word in words:
            clean = word.strip()
            if not clean:
                continue
            # Remove leading ال for comparison (but keep original for initial)
            bare = clean.lstrip("ال") if clean.startswith("ال") else clean
            if clean in skip_words or bare in skip_words:
                continue
            if clean in type_words:
                initials.append(clean[0])
                continue
            # Take the first character
            initials.append(clean[0])

        return ".".join(initials)

def get_document_footer(wilaya="", doc_date="", show_employee_signature=True):
    """
    Generate a standardized document footer.
    """
    if show_employee_signature:
        return f"""
        <br/><br/>
        <table width="100%" dir="rtl" style="margin-top: 30px;">
            <tr>
                <td style="text-align:left; width:50%;">
                    <div style="font-size:16px; font-weight:bold;">
                        {wilaya} في {doc_date}<br/>
                        المدير(ة)<br/><br/><br/>
                    </div>
                </td>
                <td style="text-align:right; width:50%;">
                    <div style="font-size:16px; font-weight:bold;">
                        إمضاء المعني(ة)<br/><br/><br/>
                    </div>
                </td>
            </tr>
        </table>
        """
    else:
        return f"""
        <br/><br/>
        <table width="100%" dir="rtl" style="margin-top: 30px;">
            <tr>
                <td style="text-align:left; width:100%;">
                    <div style="font-size:16px; font-weight:bold;">
                        {wilaya} في {doc_date}<br/>
                        المدير(ة)<br/><br/><br/>
                    </div>
                </td>
            </tr>
        </table>
        """
