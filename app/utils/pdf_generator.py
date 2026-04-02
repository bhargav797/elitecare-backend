from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import os
from io import BytesIO
from datetime import datetime
from app.models.billing import Bill

def generate_invoice_pdf(bill: Bill, patient_email: str, hospital_name: str = "Health Hospital App", first_name: str = None, last_name: str = None, profile_photo: str = None) -> BytesIO:
    PRIMARY_DARK = colors.HexColor('#070235')
    PRIMARY_INDIGO = colors.HexColor('#1e1b4b')
    SLATE_800 = colors.HexColor('#1e293b')
    SLATE_600 = colors.HexColor('#475569')
    SLATE_400 = colors.HexColor('#94a3b8')
    SLATE_100 = colors.HexColor('#f1f5f9')
    SLATE_50 = colors.HexColor('#f8fafc')
    INDIGO_50 = colors.HexColor('#eef2ff')
    INDIGO_600 = colors.HexColor('#4f46e5')
    
    PAID_BG = colors.HexColor('#e2fcf2')
    PAID_TEXT = colors.HexColor('#005236')
    PARTIAL_BG = colors.HexColor('#fffbeb')
    PARTIAL_TEXT = colors.HexColor('#d97706')
    PENDING_BG = colors.HexColor('#fef2f2')
    PENDING_TEXT = colors.HexColor('#dc2626')

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        topMargin=0.5*inch, 
        bottomMargin=0.5*inch, 
        leftMargin=0.5*inch, 
        rightMargin=0.5*inch
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Text Styles
    brand_style = ParagraphStyle('Brand', parent=styles['Normal'], fontSize=16, fontName='Helvetica-Bold', textColor=PRIMARY_DARK)
    subbrand_style = ParagraphStyle('SubBrand', parent=styles['Normal'], fontSize=9, textColor=SLATE_600, spaceAfter=8)
    contact_style = ParagraphStyle('Contact', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold', textColor=SLATE_400)
    
    inv_title = ParagraphStyle('InvTitle', parent=styles['Heading1'], fontSize=40, fontName='Helvetica-Bold', textColor=SLATE_100, alignment=TA_RIGHT, spaceAfter=0)
    label_r = ParagraphStyle('LR', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold', textColor=SLATE_400, alignment=TA_RIGHT, spaceAfter=2)
    val_r = ParagraphStyle('VR', parent=styles['Normal'], fontSize=12, fontName='Helvetica-Bold', textColor=PRIMARY_INDIGO, alignment=TA_RIGHT, spaceAfter=8)
    date_r = ParagraphStyle('DR', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold', textColor=SLATE_800, alignment=TA_RIGHT)
    
    # Logo Box
    try:
        from io import BytesIO
        import urllib.request
        from reportlab.platypus import Image
        req = urllib.request.Request("https://res.cloudinary.com/dxjc26piq/image/upload/v1773520713/logo_vlbo95.png", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            logo_data = BytesIO(response.read())
        
        # Calculate proportional size based on an absolute height, to span across
        # The logo looks like 300x70 approx, let's set height to 0.7 inch
        left_header = [Image(logo_data, height=0.7*inch, width=3*inch, kind='proportional')]
    except Exception as e:
        # Fallback in case of network issue
        left_header = [Paragraph("Health Hospital App", brand_style)]
    
    right_header = [
        Paragraph("INVOICE", inv_title), 
        Paragraph("BILL NUMBER", label_r), 
        Paragraph(f"#{bill.bill_number}", val_r), 
        Paragraph("DATE ISSUED", label_r), 
        Paragraph(bill.bill_date.strftime("%d-%m-%Y"), date_r)
    ]
    
    header_table = Table([[left_header, right_header]], colWidths=[3.7*inch, 3.5*inch])
    header_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
    elements.extend([header_table, Spacer(1, 0.4*inch)])
    
    # Patient Block
    patient_name = f"{first_name} {last_name}" if first_name else "Unregistered Patient"
    
    avatar = None
    if profile_photo:
        try:
            import urllib.request
            from io import BytesIO
            from reportlab.platypus import Image
            req = urllib.request.Request(profile_photo, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                img_data = BytesIO(response.read())
            img = Image(img_data, width=0.5*inch, height=0.5*inch, kind='proportional')
            avatar = Table([[img]], colWidths=[0.5*inch], rowHeights=[0.5*inch])
            avatar.setStyle(TableStyle([
                ('ROUNDEDCORNERS', [10, 10, 10, 10]),
                ('ALIGN', (0,0), (0,0), 'CENTER'),
                ('VALIGN', (0,0), (0,0), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0)
            ]))
        except Exception as e:
            avatar = None

    if not avatar:
        initial = patient_name[0].upper()
        avatar = Table([[Paragraph(initial, ParagraphStyle('Init', fontName='Helvetica-Bold', fontSize=14, textColor=INDIGO_600, alignment=TA_CENTER))]], colWidths=[0.5*inch], rowHeights=[0.5*inch])
        avatar.setStyle(TableStyle([('BACKGROUND', (0,0), (0,0), INDIGO_50), ('ROUNDEDCORNERS', [10, 10, 10, 10]), ('VALIGN', (0,0), (0,0), 'MIDDLE')]))
    
    p_info = Table([[avatar, Table([
        [Paragraph(patient_name, ParagraphStyle('PN', fontName='Helvetica-Bold', fontSize=11, textColor=SLATE_800))],
        [Paragraph(patient_email, ParagraphStyle('PE', fontSize=9, textColor=SLATE_600))]
    ], colWidths=[2.5*inch])]], colWidths=[0.6*inch, 2.5*inch])
    p_info.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))

    patient_col = [
        Paragraph("PATIENT INFORMATION", ParagraphStyle('PLabel', fontSize=8, fontName='Helvetica-Bold', textColor=SLATE_400, spaceAfter=8)),
        p_info,
        Spacer(1, 0.1*inch),
        Paragraph(f"PATIENT ID: <font color='#1e293b'>PID-{str(bill.patient_id).zfill(6)}</font>", ParagraphStyle('PID', fontSize=8, fontName='Helvetica-Bold', textColor=SLATE_400))
    ]
    
    # Status Block
    status_bg = PAID_BG if bill.payment_status.value == 'paid' else (PARTIAL_BG if bill.payment_status.value == 'partial' else PENDING_BG)
    status_color = PAID_TEXT if bill.payment_status.value == 'paid' else (PARTIAL_TEXT if bill.payment_status.value == 'partial' else PENDING_TEXT)
    balance_str = "Balance has been paid in full." if bill.payment_status.value == "paid" else f"Outstanding Balance: <b>Rs. {bill.remaining_amount:,.2f}</b>"
    
    badge = Table([[Paragraph(bill.payment_status.value.upper(), ParagraphStyle('Badg', fontName='Helvetica-Bold', fontSize=10, textColor=status_color, alignment=TA_CENTER))]], colWidths=[1.5*inch])
    badge.setStyle(TableStyle([('BACKGROUND', (0,0), (0,0), status_bg), ('ROUNDEDCORNERS', [8, 8, 8, 8]), ('TOPPADDING', (0,0), (0,0), 6), ('BOTTOMPADDING', (0,0), (0,0), 6), ('BOX', (0,0), (0,0), 0.5, status_color)]))
    
    # Right align the badge using a wrapper
    badge_wrapper = Table([["", badge]], colWidths=[1.8*inch, 1.5*inch])
    badge_wrapper.setStyle(TableStyle([('ALIGN', (1,0), (1,0), 'RIGHT')]))

    status_col = [
        Paragraph("PAYMENT STATUS", label_r),
        Spacer(1, 0.05*inch),
        badge_wrapper,
        Spacer(1, 0.1*inch),
        Paragraph(balance_str, ParagraphStyle('StatusBal', fontSize=9, textColor=SLATE_600, alignment=TA_RIGHT))
    ]
    
    info_table = Table([[patient_col, status_col]], colWidths=[3.5*inch, 3.5*inch])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBEFORE', (1, 0), (1, -1), 0.5, SLATE_100),
        ('LEFTPADDING', (1, 0), (1, -1), 20),
        ('RIGHTPADDING', (0, 0), (0, -1), 20)
    ]))
    
    box_table = Table([[info_table]], colWidths=[7.2*inch])
    box_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, SLATE_100),
        ('ROUNDEDCORNERS', [15, 15, 15, 15]),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
    ]))
    elements.extend([box_table, Spacer(1, 0.3*inch)])
    
    # Items Table
    th = ParagraphStyle('TH', fontSize=8, fontName='Helvetica-Bold', textColor=SLATE_400)
    thc = ParagraphStyle('THC', parent=th, alignment=TA_CENTER)
    thr = ParagraphStyle('THR', parent=th, alignment=TA_RIGHT)
    td = ParagraphStyle('TD', fontSize=9, fontName='Helvetica-Bold', textColor=SLATE_800)
    tdc = ParagraphStyle('TDC', parent=td, alignment=TA_CENTER, textColor=SLATE_600)
    tdr = ParagraphStyle('TDR', parent=td, alignment=TA_RIGHT, textColor=SLATE_600)
    
    items_data = [[
        Paragraph("DESCRIPTION", th), Paragraph("TYPE", th), Paragraph("QTY", thc),
        Paragraph("UNIT PRICE", thr), Paragraph("GST", thr), Paragraph("TOTAL", thr)
    ]]
    for item in bill.items:
        pill = Table([[Paragraph(item.item_type.value.replace('_', ' ').upper(), ParagraphStyle('Pill', fontSize=6, fontName='Helvetica-Bold', textColor=SLATE_600, alignment=TA_CENTER))]], colWidths=[0.7*inch])
        pill.setStyle(TableStyle([('BACKGROUND', (0,0), (0,0), SLATE_50), ('ROUNDEDCORNERS', [4, 4, 4, 4]), ('TOPPADDING', (0,0), (0,0), 3), ('BOTTOMPADDING', (0,0), (0,0), 3)]))
        
        gst = Paragraph(f"<font color='#94a3b8'>{item.tax_percent}%</font><br/>Rs. {item.item_tax:,.2f}", tdr)
        items_data.append([
            Paragraph(item.description, ParagraphStyle('Desc', fontName='Helvetica-Bold', fontSize=9, textColor=SLATE_800)),
            pill, Paragraph(str(item.quantity), tdc), Paragraph(f"Rs. {item.unit_price:,.2f}", tdr),
            gst, Paragraph(f"Rs. {item.item_total:,.2f}", ParagraphStyle('TDRB', parent=tdr, fontName='Helvetica-Bold', textColor=PRIMARY_DARK))
        ])
    
    items_table = Table(items_data, colWidths=[2.8*inch, 0.9*inch, 0.5*inch, 0.9*inch, 1.0*inch, 1.1*inch])
    items_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 1, SLATE_100),
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, SLATE_50),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (-1, 0), (-1, -1), SLATE_50),  # Light grey total column
    ]))
    elements.extend([items_table, Spacer(1, 0.4*inch)])
    
    # Bottom Layout
    hist_th = ParagraphStyle('HTH', fontSize=9, fontName='Helvetica-Bold', textColor=SLATE_400)
    history_box = Table([[Paragraph("No payments recorded", ParagraphStyle('NPR', fontSize=9, fontName='Helvetica-Bold', textColor=SLATE_400, alignment=TA_CENTER))]], colWidths=[3.2*inch], rowHeights=[1.0*inch])
    # Dotted line approximation
    history_box.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, SLATE_100),
        ('ROUNDEDCORNERS', [10, 10, 10, 10]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    hist_col = [Paragraph("TRANSACTION HISTORY", hist_th), Spacer(1, 0.1*inch), history_box]

    sub_b = ParagraphStyle('SubB', fontSize=9, fontName='Helvetica-Bold', textColor=SLATE_600)
    sub_v = ParagraphStyle('SubV', fontSize=9, fontName='Helvetica-Bold', textColor=SLATE_800, alignment=TA_RIGHT)
    summary_data = [
        [Paragraph("Subtotal", sub_b), Paragraph(f"Rs. {bill.subtotal:,.2f}", sub_v)],
        [Paragraph("Total Tax (GST)", sub_b), Paragraph(f"Rs. {bill.tax_amount:,.2f}", sub_v)],
    ]
    summary_data.append([
        Paragraph("GRAND TOTAL", ParagraphStyle('GT', fontSize=12, fontName='Helvetica-Bold', textColor=PRIMARY_DARK)), 
        Paragraph(f"Rs. {bill.total_amount:,.2f}", ParagraphStyle('GTV', fontSize=16, fontName='Helvetica-Bold', textColor=PRIMARY_DARK, alignment=TA_RIGHT))
    ])
    summary_data.append([
        Paragraph("Paid Amount", ParagraphStyle('PA', fontName='Helvetica-Bold', fontSize=10, textColor=PAID_TEXT)), 
        Paragraph(f"Rs. {bill.paid_amount:,.2f}", ParagraphStyle('PAV', fontName='Helvetica-Bold', fontSize=10, textColor=PAID_TEXT, alignment=TA_RIGHT))
    ])

    if bill.remaining_amount > 0:
        rem = Table([[Paragraph("Remaining Balance", ParagraphStyle('RB', fontName='Helvetica-Bold', fontSize=10, textColor=PENDING_TEXT)), Paragraph(f"Rs. {bill.remaining_amount:,.2f}", ParagraphStyle('RBV', fontName='Helvetica-Bold', fontSize=10, textColor=PENDING_TEXT, alignment=TA_RIGHT))]], colWidths=[1.8*inch, 1.4*inch])
        rem.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), PENDING_BG), ('ROUNDEDCORNERS', [8, 8, 8, 8]), ('TOPPADDING', (0,0), (0,0), 8), ('BOTTOMPADDING', (0,0), (0,0), 8)]))
        summary_data.append([rem, ""]) # Span hack

    sum_table = Table(summary_data, colWidths=[1.8*inch, 1.6*inch])
    sum_line_idx = len(summary_data) - 2 if bill.remaining_amount == 0 else len(summary_data) - 3
    sum_table.setStyle(TableStyle([
        ('LINEBELOW', (0, sum_line_idx-1), (1, sum_line_idx-1), 1, SLATE_100),
        ('LINEBELOW', (0, sum_line_idx), (1, sum_line_idx), 1, SLATE_100),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('SPAN', (0, len(summary_data)-1), (1, len(summary_data)-1)) if bill.remaining_amount > 0 else ('TOPPADDING', (0, 0), (0, 0), 0)
    ]))
    
    sum_box_table = Table([[sum_table]], colWidths=[3.6*inch])
    sum_box_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, SLATE_100),
        ('ROUNDEDCORNERS', [15, 15, 15, 15]),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0,0), (-1,-1), SLATE_50)
    ]))
    
    bottom_layout = Table([[hist_col, sum_box_table]], colWidths=[3.4*inch, 3.8*inch])
    bottom_layout.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
    elements.extend([bottom_layout, Spacer(1, 0.5*inch)])
    
    foot_table = Table([
        [Paragraph("THANK YOU FOR CHOOSING OUR SERVICES!", ParagraphStyle('FT1', fontSize=10, fontName='Helvetica-Bold', textColor=SLATE_800, alignment=TA_CENTER))] ,
        [Paragraph("This is a computer generated digital invoice and does not require a physical signature.", ParagraphStyle('FT2', fontSize=8, fontName='Helvetica-Bold', textColor=SLATE_400, alignment=TA_CENTER))]
    ], colWidths=[7.2*inch])
    foot_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    elements.append(foot_table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer
