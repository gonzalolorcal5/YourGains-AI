from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime
import json
from typing import Dict, Any


def generate_routine_pdf(plan_data: Dict[str, Any], user_email: str = "usuario") -> bytes:
    """
    Genera un PDF profesional con la rutina y dieta del usuario.
    
    Args:
        plan_data: Diccionario con rutina, dieta y motivación
        user_email: Email del usuario para personalización
    
    Returns:
        bytes: Contenido del PDF generado
    """
    from io import BytesIO
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, 
                           topMargin=60, bottomMargin=50)
    
    # Estilos personalizados
    styles = getSampleStyleSheet()
    
    # Título principal
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#84cc16'),
        fontName='Helvetica-Bold'
    )
    
    # Subtítulos principales
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=18,
        spaceAfter=15,
        spaceBefore=25,
        textColor=colors.HexColor('#84cc16'),
        fontName='Helvetica-Bold',
        borderWidth=1,
        borderColor=colors.HexColor('#84cc16'),
        borderPadding=8,
        backColor=colors.HexColor('#f0f9ff')
    )
    
    # Subtítulos de sección
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading3'],
        fontSize=14,
        spaceAfter=10,
        spaceBefore=15,
        textColor=colors.HexColor('#1e40af'),
        fontName='Helvetica-Bold'
    )
    
    # Texto normal
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        fontName='Helvetica'
    )
    
    # Texto de ejercicios
    exercise_style = ParagraphStyle(
        'ExerciseStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4,
        leftIndent=15,
        fontName='Helvetica'
    )
    
    # Texto de información del usuario
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8,
        alignment=TA_CENTER,
        textColor=colors.grey,
        fontName='Helvetica-Oblique'
    )
    
    # Construir el contenido del PDF
    story = []
    
    # Título principal con logo simulado
    story.append(Paragraph("🏋️ YourGains AI", title_style))
    story.append(Paragraph("Plan Personalizado de Entrenamiento y Nutrición", 
                          ParagraphStyle('Subtitle', parent=styles['Heading2'], 
                                       fontSize=16, alignment=TA_CENTER, 
                                       textColor=colors.HexColor('#6b7280'),
                                       fontName='Helvetica')))
    story.append(Spacer(1, 15))
    
    # Información del usuario y fecha en una tabla
    info_data = [
        ['Usuario:', user_email],
        ['Fecha de generación:', datetime.now().strftime('%d/%m/%Y %H:%M')],
        ['Generado por:', 'YourGains AI - Tu entrenador personal con IA']
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#84cc16')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 25))
    
    # Rutina
    if 'rutina' in plan_data and plan_data['rutina']:
        story.append(Paragraph("🏋️ TU RUTINA DE ENTRENAMIENTO", subtitle_style))
        
        rutina = plan_data['rutina']
        if isinstance(rutina, str):
            rutina = json.loads(rutina)
        
        if 'dias' in rutina and rutina['dias']:
            for i, dia in enumerate(rutina['dias'], 1):
                # Título del día con fondo
                story.append(Paragraph(f"Día {i}: {dia.get('nombre', f'Día {i}')}", 
                                     section_style))
                
                # Ejercicios en tabla
                if 'ejercicios' in dia and dia['ejercicios']:
                    exercise_data = [['Ejercicio', 'Series', 'Repeticiones']]
                    for ejercicio in dia['ejercicios']:
                        exercise_data.append([
                            ejercicio.get('nombre', 'Ejercicio'),
                            str(ejercicio.get('series', 'N/A')),
                            str(ejercicio.get('reps', 'N/A'))
                        ])
                    
                    exercise_table = Table(exercise_data, colWidths=[3*inch, 1*inch, 1.5*inch])
                    exercise_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#84cc16')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('TOPPADDING', (0, 0), (-1, -1), 6),
                        ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ]))
                    
                    story.append(exercise_table)
                else:
                    story.append(Paragraph("• Sin ejercicios especificados", exercise_style))
                
                story.append(Spacer(1, 12))
        
        # Consejos de rutina
        if 'consejos' in rutina and rutina['consejos']:
            story.append(Paragraph("💡 Consejos de Entrenamiento", 
                                 ParagraphStyle('TipsTitle', parent=styles['Heading4'], 
                                              fontSize=12, spaceAfter=8, 
                                              textColor=colors.HexColor('#1e40af'),
                                              fontName='Helvetica-Bold')))
            
            for consejo in rutina['consejos']:
                story.append(Paragraph(f"• {consejo}", 
                                     ParagraphStyle('TipStyle', parent=styles['Normal'],
                                                  fontSize=10, spaceAfter=3,
                                                  leftIndent=15, fontName='Helvetica')))
        
        story.append(Spacer(1, 25))
    
    # Dieta
    if 'dieta' in plan_data and plan_data['dieta']:
        story.append(Paragraph("🍎 TU PLAN DE NUTRICIÓN", subtitle_style))
        
        dieta = plan_data['dieta']
        if isinstance(dieta, str):
            dieta = json.loads(dieta)
        
        # Resumen de la dieta
        if 'resumen' in dieta and dieta['resumen']:
            story.append(Paragraph("📋 Resumen del Plan", 
                                 ParagraphStyle('SummaryTitle', parent=styles['Heading4'], 
                                              fontSize=12, spaceAfter=6, 
                                              textColor=colors.HexColor('#1e40af'),
                                              fontName='Helvetica-Bold')))
            story.append(Paragraph(dieta['resumen'], normal_style))
            story.append(Spacer(1, 15))
        
        # Comidas
        if 'comidas' in dieta and dieta['comidas']:
            for i, comida in enumerate(dieta['comidas'], 1):
                # Título de la comida
                comida_title = f"{comida.get('nombre', f'Comida {i}')}"
                if 'kcal' in comida:
                    comida_title += f" - {comida['kcal']} kcal"
                story.append(Paragraph(comida_title, section_style))
                
                # Alimentos en tabla
                if 'alimentos' in comida and comida['alimentos']:
                    food_data = [['Alimento']]
                    for alimento in comida['alimentos']:
                        food_data.append([alimento])
                    
                    food_table = Table(food_data, colWidths=[5*inch])
                    food_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                        ('TOPPADDING', (0, 0), (-1, -1), 4),
                        ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ]))
                    
                    story.append(food_table)
                
                # Macros si están disponibles
                if 'macros' in comida and comida['macros']:
                    macros = comida['macros']
                    macros_data = [
                        ['Proteínas', f"{macros.get('proteinas', 'N/A')}g"],
                        ['Hidratos', f"{macros.get('hidratos', 'N/A')}g"],
                        ['Grasas', f"{macros.get('grasas', 'N/A')}g"]
                    ]
                    
                    macros_table = Table(macros_data, colWidths=[1.5*inch, 1*inch])
                    macros_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6b7280')),
                        ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                        ('TOPPADDING', (0, 0), (-1, -1), 2),
                        ('LEFTPADDING', (0, 0), (-1, -1), 0),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ]))
                    
                    story.append(Paragraph("Macros:", 
                                         ParagraphStyle('MacrosTitle', parent=styles['Normal'],
                                                      fontSize=9, spaceAfter=3,
                                                      textColor=colors.HexColor('#6b7280'),
                                                      fontName='Helvetica-Bold')))
                    story.append(macros_table)
                
                story.append(Spacer(1, 12))
        
        # Consejos de nutrición
        if 'consejos_finales' in dieta and dieta['consejos_finales']:
            story.append(Paragraph("💡 Consejos de Nutrición", 
                                 ParagraphStyle('TipsTitle', parent=styles['Heading4'], 
                                              fontSize=12, spaceAfter=8, 
                                              textColor=colors.HexColor('#1e40af'),
                                              fontName='Helvetica-Bold')))
            
            for consejo in dieta['consejos_finales']:
                story.append(Paragraph(f"• {consejo}", 
                                     ParagraphStyle('TipStyle', parent=styles['Normal'],
                                                  fontSize=10, spaceAfter=3,
                                                  leftIndent=15, fontName='Helvetica')))
        
        story.append(Spacer(1, 25))
    
    # Motivación
    if 'motivacion' in plan_data and plan_data['motivacion']:
        motivacion = plan_data['motivacion']
        if isinstance(motivacion, str) and motivacion.startswith('"'):
            motivacion = json.loads(motivacion)
        
        story.append(Paragraph("💪 MENSAJE DE MOTIVACIÓN", subtitle_style))
        
        # Crear un cuadro destacado para la motivación
        motivacion_box = Paragraph(motivacion, 
                                 ParagraphStyle('MotivationBox', parent=styles['Normal'],
                                              fontSize=11, alignment=TA_CENTER,
                                              textColor=colors.HexColor('#1e40af'),
                                              fontName='Helvetica-Bold',
                                              borderWidth=2,
                                              borderColor=colors.HexColor('#84cc16'),
                                              borderPadding=15,
                                              backColor=colors.HexColor('#f0f9ff')))
        story.append(motivacion_box)
        story.append(Spacer(1, 25))
    
    # Footer con información adicional
    story.append(Spacer(1, 20))
    
    # Línea separadora
    story.append(Paragraph("─" * 50, 
                         ParagraphStyle('Separator', parent=styles['Normal'],
                                      fontSize=8, alignment=TA_CENTER,
                                      textColor=colors.lightgrey)))
    story.append(Spacer(1, 10))
    
    # Información del footer
    footer_data = [
        ['⚠️ Importante:', 'Consulta con un profesional de la salud antes de comenzar'],
        ['🤖 Generado por:', 'YourGains AI - Tu entrenador personal con IA'],
        ['📱 Más información:', 'Visita tu dashboard en YourGains AI'],
        ['📅 Fecha:', datetime.now().strftime('%d/%m/%Y %H:%M')]
    ]
    
    footer_table = Table(footer_data, colWidths=[1.5*inch, 4*inch])
    footer_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6b7280')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#4b5563')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    
    story.append(footer_table)
    
    # Construir el PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
