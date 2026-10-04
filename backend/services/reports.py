from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from pathlib import Path
from datetime import datetime

def create_report(record, output):
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=18*mm,leftMargin=18*mm,topMargin=18*mm,bottomMargin=18*mm)
    styles=getSampleStyleSheet(); styles.add(ParagraphStyle(name="Small",parent=styles["BodyText"],fontSize=8,leading=11,textColor=colors.HexColor('#526174')))
    story=[Paragraph("AI WELDING INSPECTION REPORT",styles['Title']),Paragraph("AI-Driven Welding Inspection & Quality Reporting Framework",styles['Normal']),Spacer(1,8*mm)]
    meta=[["Inspection ID",record['inspection_id'],"Report ID", "RPT-"+record['inspection_id'].replace('WELD-','')], ["Date / Time",record['timestamp'],"Inspector","AI Inspection System"]]
    t=Table(meta,colWidths=[28*mm,58*mm,25*mm,55*mm]); t.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),colors.HexColor('#eaf0f6')),('BACKGROUND',(2,0),(2,-1),colors.HexColor('#eaf0f6')),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#d5dee8')),('FONTNAME',(0,0),(-1,-1),'Helvetica'),('FONTSIZE',(0,0),(-1,-1),8),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)])); story += [t,Spacer(1,6*mm)]
    imgs=[]
    for label,key in [('INPUT IMAGE','image_path'),('AI ANNOTATED IMAGE','annotated_path')]:
        p=Path(record[key])
        if p.exists():
            story.append(Paragraph(label,styles['Heading2'])); im=Image(str(p),width=78*mm,height=48*mm); im._preserveAspectRatio=True; imgs.append(im)
    if imgs:
        if len(imgs)==2:
            tab=Table([[imgs[0],imgs[1]],[Paragraph('Input weld image',styles['Small']),Paragraph('Prototype AI region overlay',styles['Small'])]],colWidths=[82*mm,82*mm]); tab.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),2),('RIGHTPADDING',(0,0),(-1,-1),2)])); story.append(tab)
        else: story.extend(imgs)
    story += [Spacer(1,5*mm),Paragraph('INSPECTION RESULT',styles['Heading2'])]
    result=[["Defect Type",record['defect_type'],"Confidence",f"{record['confidence']:.0%}"],["Severity",record['severity'],"Overall Verdict",record['verdict']],["Processing Time",f"{record['processing_time']:.2f} sec","Analysis","Prototype AI" if record['analysis_mode']=='prototype_fallback' else 'Model']]
    rt=Table(result,colWidths=[28*mm,55*mm,28*mm,55*mm]); rt.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.HexColor('#d5dee8')),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#eaf0f6')),('BACKGROUND',(2,0),(2,-1),colors.HexColor('#eaf0f6')),('FONTSIZE',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)])); story += [rt,Spacer(1,4*mm),Paragraph('AI ANALYSIS SUMMARY',styles['Heading2']),Paragraph(record['summary'],styles['BodyText']),Paragraph('INSPECTION PIPELINE',styles['Heading2']),Paragraph('Image Collection  →  Preprocessing  →  AI Analysis  →  Defect Detection  →  Quality Verdict',styles['BodyText']),Paragraph('TECHNOLOGY',styles['Heading2']),Paragraph('Python · OpenCV · Machine Learning · Deep Learning architecture',styles['BodyText']),Spacer(1,4*mm),Paragraph('DISCLAIMER',styles['Heading2']),Paragraph('This prototype is intended for demonstration and academic evaluation. Results should not be used as a substitute for certified industrial welding inspection.',styles['Small'])]
    def footer(canvas,doc):
        canvas.saveState(); canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#64748b')); canvas.drawString(18*mm,10*mm,'AI Welding Inspection · '+record['inspection_id']); canvas.drawRightString(192*mm,10*mm,f'Page {doc.page}'); canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return str(output)
