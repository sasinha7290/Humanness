import streamlit as st
import re
import xml.etree.ElementTree as ET
import io
import base64
from pathlib import Path
import pandas as pd
from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from PIL import Image as PILImage
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Image,
    Paragraph,
    PageBreak,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.piecharts import Pie
############
import streamlit as st
import re
import xml.etree.ElementTree as ET
import io
import pandas as pd
from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from PIL import Image as PILImage
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Image,
    Paragraph,
    PageBreak,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.piecharts import Pie


# ============================================================
# COMPASS Humanness Calculator
# ============================================================

st.set_page_config(
    page_title="COMPASS Humanness Calculator",
    page_icon="",
    layout="centered"
)


# ============================================================
# Flexible scoring configuration
# ============================================================

TOTAL_HUMANNESS_SCORE = 100


# ============================================================
# Question bank
# Total configured score = 100 / 100
# ============================================================


QUESTIONS = [
    # -----------------------------
    # Data Training
    # -----------------------------
    {
        "id": "h_body",
        "group": "Model Training Module",
        "section": "Model Building",
        "is_gate": True,
        "question": "<div class = 'content'>Was the original ML model built from human tissues or body fluids (blood, <div class = 'definition'>BAL<span class = 'definitiontext'>Bronchoalveolar lavage (BAL): Fluid collected from the lower airways during bronchoscopy. BAL contains immune cells, proteins, microbes, and soluble biomarkers that directly reflect lung biology.</span></div>, etc.)?</div>",
        "clean_question": "Was the original ML model built from human tissues or body fluids (blood, BAL, etc.)?",
        "type": "single_choice",
        "options": {
            "Yes": 0,
            "No": 0
        },
        "max_points": 0,
    },
    {
        "id": "cc_anchoring",
        "group": "Model Training Module",
        "section": "Cross-Cohort Anchoring",
        "is_gate": False,
        "question": "Were independent human cohorts used to build and refine the model?",
        "type": "single_choice",
        "options": {
            "Yes": 5,
            "No": 0,
        },
        "max_points": 5,
    },
    {
        "id": "td_size",
        "group": "Model Training Module",
        "section": "<div class='tooltip'>Training Dataset Size<span class='tooltiptext'>Sample size should reflect independent human specimens and biological diversity, not technical replication. Longitudinal samples from the same individual may be included when they represent distinct biological states (e.g., pre/post treatment or disease progression).</span></div>",
        "is_gate": False,
        "question": "What is the total number of samples in the training dataset?",
        "type": "single_choice",
        "options": {
            ">5,000": 25,
            "1,001-5,000": 20,
            "501-1,000": 15,
            "100-500": 10,
            "<100": 5,
        },
        "max_points": 25,
    },
    {
        "id": "data_quality",
        "group": "Model Training Module",
        "section": "Data Quality of Training Dataset",
        "is_gate": False,
        "question": "What was the quality of the dataset(s) used to build the model?",
        "type": "single_choice",
        "options": {
            "High Quality: Deep sequencing, >50M reads/sample, validated platforms": 10,
            "Low Quality: <50M reads/sample, unvalidated platforms": 5,
            "Unknown: Insufficient Information": 0,
        },
        "max_points": 10,
    },

    # -----------------------------
    # Data Validation
    # -----------------------------
    {
        "id": "independent_cohort_validation",
        "group": "Model Validation Module",
        "section": "<div class='tooltip'>Independent Cohort Validation<span class='tooltiptext'>Evaluation in one or more independent human cohorts not used for model development. Demonstrates generalizability and reduces the risk of overfitting.</span></div>",
        "is_gate": True,
        "question": "Was the model evaluated on an independent human cohort not used in training?",
        "type": "single_choice",
        "options": {
            "Yes": 0,
            "No": 0,
        },
        "max_points": 0,
    },
    {
        "id": "total_sample_size",
        "group": "Model Validation Module",
        "section": "<div class='tooltip'>Total Sample Size<span class='tooltiptext'>Sample size should reflect independent human specimens and biological diversity, not technical replication. Longitudinal samples from the same individual may be included when they represent distinct biological states (e.g., pre/post treatment or disease progression).</span></div>",
        "is_gate": False,
        "question": "What is the total number of human samples used in model development (training + validation)?",
        "type": "single_choice",
        "options": {
            ">10,000 unique samples": 25,
            "5,001–10,000 unique samples": 20,
            "1,001–5,000 unique samples": 15,
            "500–1,000 unique samples": 10,
            "<500 unique samples": 5,
        },
        "max_points": 25,
    },
    {
        "id": "training_classification_accuracy",
        "group": "Model Validation Module",
        "section": "<div class='tooltip'>Cross-Cohort Accuracy<span class='tooltiptext'>Measures consistency across independent human cohorts and helps identify models that are overfit to a single training dataset.</span></div>",
        "is_gate": False,
        "question": "What is the classification accuracy in the training dataset?",
        "type": "single_choice",
        "options": {
            "AUC > 90": 25,
            "AUC > 80": 15,
            "AUC > 70": 8,
            "AUC < 70": 0,
        },
        "max_points": 25,
    },
    {
        "id": "cc_conservation",
        "group": "Additional Support Module",
        "section": "Cross-Species Conservation",
        "is_gate": False,
        "question": "<div class = 'container'> Is the entity conserved across <div class='definition'>species<span class='definitiontext'>A biological organism (e.g., human, mouse, rat, non-human primate) used to generate or validate findings. Human-derived evidence contributes to Humanness; cross-species conservation provides supportive, but not primary, evidence.</span></div>?</div>",
        "clean_question": "Is the entity conserved across species?",
        "type": "single_choice",
        "options": {
            "Yes (e.g., mouse, rat, non-human primate, etc.)": 10,
            "No": 0,
        },
        "max_points": 10,
    },
    {
        "id": "dataset_composition",
        "group": "Module Relevance Module",
        "section": "Human Disease Context in Training and/or Validation Datasets",
        "is_gate": False,
        "question": "What is the healthy/disease composition of the training and validation datasets?",
        "type": "single_choice",
        "options": {
            "Healthy + disease controls; >50% disease samples": 25,
            "Healthy + disease controls; <50% disease samples": 15,
            "Healthy only or disease only samples": 5,
            "Unknown/unclear": 0,
        },
        "max_points": 25,
    },
    {
        "id": "disease_severity",
        "group": "Module Relevance Module",
        "section": "Disease Severity / Outcome Classification",
        "is_gate": False,
        "question": "<div class = 'container'>Was the model originally built or independently validated to classify <div class='definition'>disease severity<span class='definitiontext'>The extent or stage of illness (e.g., mild, moderate, severe, progressive, remission, relapse). Models linked to disease severity are expected to better capture clinically meaningful biology.</span></div>, progression, therapeutic response, relapse, survival, or <div class='definition'>clinical outcomes<span class='definitiontext'>Patient-centered endpoints such as disease-free, transplant-free or overall survival, disease progression (complications, by symptoms or radiologic or other clinically accepted scores), relapse, treatment response, symptom improvement, hospitalization or mortality in hospital, or adverse events that determine clinical benefit typically in Phase 3 trials looking for efficacy.</span></div>?</div>",
        "clean_question": "Was the model originally built or independently validated to classify disease severity, progression, therapeutic response, relapse, survival, or clinical outcomes?",
        "type": "single_choice",
        "options": {
            "Yes, and it was prospectively validated": 25,
            "Yes, and it was retrospectively validated": 15,
            "Exploratory association only": 5,
            "No, the model was not built with these objectives": 0,
        },
        "max_points": 25,
    },
    {
        "id": "human_cohort_validation",
        "group": "Module Relevance Module",
        "section": "Prospective Human Cohort Validation",
        "is_gate": False,
        "question": "<div class = 'container'>Were datasets prospectively collected with future outcomes annotated after <div class='definition'>tissue diversion<span class='definitiontext'>The time at which a human specimen is collected from clinical care or surgery for research. Prospective outcome studies link future clinical events to samples obtained at the time of tissue diversion.</span></div>?</div>",
        "clean_question": "Were datasets prospectively collected with future outcomes annotated after tissue diversion?",
        "type": "single_choice",
        "options": {
            ">5 cohorts": 25,
            "3-5 cohorts": 15,
            "1-2 cohorts": 10,
            "Retrospective only": 5,
            "Outcome-linked cohorts not available": 0,
        },
        "max_points": 25,
    },
    {
        "id": "gwas_support",
        "group": "Module Relevance Module",
        "section": "GWAS or Other Causal Biological Support",
        "is_gate": False,
        "question": "<div class = 'container'>Does the discovered entity have <div class='definition'>GWAS<span class='definitiontext'>A study that identifies genetic variants associated with human traits or disease. Within TRUST-NAM, GWAS is one example of human biological support, alongside rare variants, eQTLs, CRISPR, drug-target evidence, and other causal data.</span></div> support or other causal biological support (e.g., epigenetic, environmental, microbial, or pharmacoepidemiological mechanisms)?</div>",
        "clean_question": "Does the discovered entity have GWAS support or other causal biological support (e.g., epigenetic, environmental, microbial, or pharmacoepidemiological mechanisms)?",
        "type": "single_choice",
        "options": {
            "Yes": 25,
            "No": 0,
        },
        "max_points": 25,
    },
    {
        "id": "nam_sample_size",
        "group": "Biological Fidelity",
        "section": "<div class='tooltip'>Sample Size<span class='tooltiptext'>For patient-derived NAM studies, the calculated sample size should refer to independent biological repliactes (unique human donors or specimens), not technical replicates such as wells, organoids, passages, fields of view, or cells. See also Reproducibility Modifier (below) for assessing if the study is adequately powered.</span></div>",
        "is_gate": False,
        "question": "What is the AUC ROC in healthy vs disease.",
        "type": "single_choice",
        "options": {
            ">0.85": 20,
            "0.70-0.84": 10,
            "<0.70": 0,
        },
        "max_points": 20,
    },
    {
        "id": "auc_roc",
        "group": "Biological Fidelity",
        "section": "Signature Capture (AUC ROC)",
        "is_gate": False,
        "question": "What is the AUC ROC in healthy vs disease.",
        "type": "single_choice",
        "options": {
            ">0.85": 20,
            "0.70-0.84": 10,
            "<0.70": 0,
        },
        "max_points": 20,
    },
    {
        "id": "perturbation_alignment",
        "group": "Biological Fidelity",
        "section": "Perturbation Alignment (Multi-omic + Phenotype)",
        "is_gate": False,
        "question": "<div class = 'content'>What is the alignment of <div class = 'definition'>perturbation<span class = 'definitiontext'>An intentional experimental intervention (drug, gene editing, cytokine, infection, environmental stimulus, etc.) used to test whether a NAM responds as predicted from human biology.</span></div> effects with model-predicted biology.</div>",
        "clean_question": "What is the alignment of perturbation effects with model-predicted biology.",
        "type": "single_choice",
        "options": {
            ">3 independent readout types": 20,
            "1-3 independent readout types": 10,
            "Not applicable": 0,
        },
        "max_points": 20,
    },
    {
        "id": "outcome_prediction",
        "group": "Biological Fidelity",
        "section": "Outcome Prediction (Prospective Human Cohort)",
        "is_gate": False,
        "question": "<div class = 'content'>Does post-<div class = 'definition'>perturbation<span class = 'definitiontext'>An intentional experimental intervention (drug, gene editing, cytokine, infection, environmental stimulus, etc.) used to test whether a NAM responds as predicted from human biology.</span></div> signature predict prospective human outcomes?</div>",
        "clean_question": "Does post-perturbation signature predict prospective human outcomes?",
        "type": "single_choice",
        "options": {
            "Yes, AUC ROC > 0.85": 20,
            "Yes, AUC ROC 0.70 - 0.84": 10,
            "No or restrospective only or AUC < 0.70": 0,
        },
        "max_points": 20,
    },
    {
        "id": "animal_model_corroboration",
        "group": "Biological Fidelity",
        "section": "Animal Model Corroboration (Translational Consistency)",
        "is_gate": False,
        "question": "Does animal model recapitulate and translate findings?",
        "type": "select_all",
        "options": {
            "AUC ROC > 0.75 (Healthy vs Disease)": 0,
            "Predicts functional/phenotypic outcomes (AUC ROC > 0.6)": 0,
            "Correlation >0.70 with prediction model signature post-perturbation": 0,
            "Post-perturbation signature predicts outcomes in human cohort (AUC ROC > 0.60)": 0,
        },
        "rubric": {
            0: 0,
            1: 0,
            2: 5,
            3: 5,
            4: 10,
        },
        "max_points": 10,
    },
    {
        "id": "reproducibility",
        "group": "Biological Fidelity",
        "section": "Reproducibility/Adoption Modifier",
        "is_gate": False,
        "question": "Select all that apply",
        "type": "toggle",
        "options": {
            "Minimal components, easy to implement, low technical complexity.": 4,
            "High throughput, cost-effective, readily scalable.": 1,
            "Physiologically relevant, minimal exogenous manipulation.": 1,
            "Clear indications, limitations, and intended use.": 2,
            "SOPs available, validated, and widely adpoted.": 4,
            "Adequate biological replicates (unique donors), technical replicates, statistically powered.": 10,
            "Systematically evaluated for passage stability and drift.": 4,
            "Benchmarked against appropriate state-of-the-art standards.": 4,

        },
        "max_points": 30,
    },
]

def calculate_score(responses):
    score = 0

    for q in QUESTIONS:
        selected_answer = responses.get(q["id"])
        
        if q["type"] == "single_choice":
            if selected_answer:
                score += q["options"].get(selected_answer, 0)
        elif q["type"] == "select_all":
            if selected_answer:
                score += q["rubric"].get(len(selected_answer), 0)
        elif q["type"] == "toggle":
            if selected_answer:
                for i in range(len(selected_answer)):
                    if selected_answer[i]:
                        score += list(q["options"].values())[i]

    return round(score, 1)

def get_interpretation(score):
    """
    Gives a simple interpretation based on current humanness score.
    This can be refined later as the calculator matures.
    """

    if score >= 80:
        return "High humanness: the model appears strongly anchored to human biology."
    elif score >= 60:
        return "Moderate-to-high humanness: the model has substantial human relevance."
    elif score >= 40:
        return "Partial humanness: the model has meaningful human relevance but important gaps remain."
    elif score >= 20:
        return "Low-to-moderate humanness: the model has some human anchoring but limited validation."
    else:
        return "Low humanness: the current evidence for human biological relevance is limited."
    
def get_relevance_interpretation(score):
    if score >= 80:
        return "Strongly clinically relevant."
    elif score >= 60:
        return "Moderately relevant."
    elif score >= 40:
        return "Weakly relevant."
    else:
        return "Limited translational relevance."

def human_silhouette_svg(score):
    """
    Creates a human silhouette that fills from bottom to top according to score.
    The fill uses a warm gradient color.
    """

    # Visible silhouette boundary
    human_top = 21
    human_bottom = 350
    human_height = human_bottom - human_top

    fill_height = (score / 100) * human_height
    fill_y = human_bottom - fill_height

    svg = f"""
    <div style="width:100%; text-align:center; margin-top:20px;">

        <svg width="240" height="390" viewBox="0 0 240 390" xmlns="http://www.w3.org/2000/svg">

            <defs>
                <linearGradient id="warmGradient" x1="0%" y1="100%" x2="0%" y2="0%">
                    <stop offset="0%" style="stop-color:#facc15; stop-opacity:1" />
                    <stop offset="45%" style="stop-color:#fb923c; stop-opacity:1" />
                    <stop offset="100%" style="stop-color:#dc2626; stop-opacity:1" />
                </linearGradient>

                <clipPath id="humanClip">
                    <!-- Head -->
                    <circle cx="120" cy="55" r="34"/>

                    <!-- Torso -->
                    <rect x="78" y="90" width="84" height="138" rx="34"/>

                    <!-- Left arm -->
                    <rect x="38" y="112" width="34" height="125" rx="17"/>

                    <!-- Right arm -->
                    <rect x="168" y="112" width="34" height="125" rx="17"/>

                    <!-- Left leg -->
                    <rect x="84" y="225" width="34" height="125" rx="17"/>

                    <!-- Right leg -->
                    <rect x="122" y="225" width="34" height="125" rx="17"/>
                </clipPath>
            </defs>

            <!-- Background silhouette -->
            <g clip-path="url(#humanClip)">
                <rect x="0" y="0" width="240" height="360" fill="#e5e7eb"/>
            </g>

            <!-- Filled score silhouette -->
            <g clip-path="url(#humanClip)">
                <rect
                    x="0"
                    y="{fill_y}"
                    width="240"
                    height="{fill_height}"
                    fill="url(#warmGradient)"
                />
            </g>

            <!-- Score label -->
            <text
                x="120"
                y="382"
                text-anchor="middle"
                font-size="24"
                font-family="Arial"
                font-weight="bold"
                fill="#111827"
            >
                {score}% Humanness
            </text>

        </svg>

    </div>
    """

    return svg

def generate_pdf_report(h_resp, r_resp, n_resp, h_score, r_score, n_score, user_id):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()

    def render_metric(image_path, color, score, resp, score_name, score_desc):

        pil_img = PILImage.open(image_path)
        alpha = pil_img.split()[3]
        color_block = PILImage.new("RGBA", pil_img.size, color)

        tinted_img = PILImage.composite(color_block, pil_img, alpha)

        img_buffer = io.BytesIO()
        tinted_img.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        image = Image(img_buffer, width=100, height=100)
        pie = render_pie(score, color, resp)
        title = Paragraph(score_name, ParagraphStyle('ScoreTitle', parent=styles['Heading2'], fontSize=16, leading=20, textColor=colors.Color(color[0]/255, color[1]/255, color[2]/255, alpha=color[3]/255), alignment=1))
        description = Paragraph(score_desc, ParagraphStyle('ScoreDescription', parent=styles['Normal'], fontSize=12, leading=16, textColor=colors.Color(color[0]/255, color[1]/255, color[2]/255, alpha=color[3]/255), alignment=1))

        data = [[image, [title, Spacer(1, 6), description], pie]]

        col_widths = [150, 200, 175]



        box_table = Table(data, colWidths = col_widths)
        box_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1.5, colors.Color(color[0]/255, color[1]/255, color[2]/255, alpha=color[3]/255)),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ROUNDEDCORNERS', [10, 10, 10, 10]), 
        ]))

        box_table.spaceBefore = 10
        box_table.spaceAfter = 10


        return box_table
    
    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Heading1'], fontSize=22, leading=26,
        textColor=colors.HexColor('#0F172A'), spaceAfter=12, alignment=1
    )
    heading_style = ParagraphStyle(
        'SectionHeading', parent=styles['Heading2'], fontSize=14, leading=18,
        textColor=colors.HexColor('#1E3A8A'), spaceBefore=16, spaceAfter=8, keepWithNext=True
    )
    body_style = ParagraphStyle(
        'BodyTextCustom', parent=styles['Normal'], fontSize=10, leading=14,
        textColor=colors.HexColor('#334155')
    )
    bold_style = ParagraphStyle(
        'BoldTextCustom', parent=body_style, fontName='Helvetica-Bold'
    )
    
    story = []

    def render_pie(score, color, resp):
        chart_drawing = Drawing(width=400, height=120)

        pc = Pie()
        pc.x = 150         
        pc.y = 10        
        pc.width = 100      
        pc.height = 100 
        pc.data = [35, 25, 20, 20]

        pc.innerRadiusFraction = 0.75 
        chart_drawing.add(pc)

        if not resp:
            pc.data = [100, 0]
        else:
            data = [calculate_score({key: value}) for key, value in resp.items()]
            data.append(100 - sum(data))
            data.sort(reverse=True)
            pc.data = data

        for i in range(0, len(pc.data)):
            pc.slices[i].fillColor = colors.Color(color[0]/255, color[1]/255, color[2]/255, alpha=color[3]/255 * i/(len(pc.data)-1) if len(pc.data) > 1 else 1)


        center_text = String(
            pc.x + (pc.width / 2), 
            pc.y + (pc.height / 2) - 12,            
            f"{score}",        
            textAnchor='middle',     
            fontName='Helvetica-Bold',
            fontSize=36,
            fillColor= colors.Color(color[0]/255, color[1]/255, color[2]/255, alpha=color[3]/255)
        )
        chart_drawing.add(center_text)

        return chart_drawing
    
    story.append(Image("images/inetmed_letterhead.png", width = 600, height = 110))
    
    story.append(Paragraph("TRUST-NAM Assessment Results", title_style))
    story.append(Spacer(1, 15))
    story.append(render_metric("images/human.png", (30, 75, 150, 255), h_score, h_resp, "HUMANNESS SCORE", "Measures how strongly a discovery or model is anchored in real human biology."))
    story.append(render_metric("images/relevance.png", (80, 120, 60, 255), r_score, r_resp, "RELEVANCE SCORE", "Measures how closely a model connects to clinically meaningful disease states, outcomes, and treatment responses."))
    story.append(render_metric("images/nam.png", (200, 150, 60, 255), n_score, n_resp, "NAM FIDELITY SCORE", "Measures how faithfully and reproducibly a NAM captures human disease biology in a scalable, fit-for-purpose manner."))

    story.append(PageBreak())

    user_data = [[Paragraph("<b>Information</b>", bold_style), Paragraph("", body_style)]] + [ 
        [Paragraph(f"<b>{ukey.capitalize()}</b>", bold_style), Paragraph(f"{uvalue}", body_style)] for ukey, uvalue in user_id.items()
    ]
    
    user_data_table = Table(user_data, colWidths=[265, 265])
    user_data_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
    ]))

    story.append(Paragraph("Recipient Information", heading_style))

    story.append(user_data_table)

    story.append(Spacer(1, 10))

    story.append(Paragraph("Score Summary", heading_style))

    summary_data = [
        [Paragraph("<b>Index Module</b>", bold_style), Paragraph("<b>Score</b>", bold_style), Paragraph("<b>Classification Benchmark</b>", bold_style)],
        [Paragraph("Humanness Index", body_style), Paragraph(f"<b>{h_score}%</b>", body_style), Paragraph(get_interpretation(h_score), body_style)],
        [Paragraph("Relevance Index", body_style), Paragraph(f"<b>{r_score}%</b>", body_style), Paragraph(get_relevance_interpretation(r_score), body_style)],
        [Paragraph("NAM Fidelity Index", body_style), Paragraph(f"<b>{n_score}%</b>", body_style), Paragraph("Evaluated biological fidelity and translational consistency.", body_style)]
    ]
    
    summary_table = Table(summary_data, colWidths=[130, 60, 340])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
    ]))

    story.append(summary_table)

    story.append(PageBreak())
    
    # Helper to clean and build response logs
    def append_breakdown(title, module_responses):
        story.append(Paragraph(title, heading_style))
        table_data = [[Paragraph("<b>Question/Section</b>", bold_style), Paragraph("<b>Selected Evaluation</b>", bold_style), Paragraph("<b>Score</b>", bold_style)]]
        footnotes = {}
        counter = 0
        for q in QUESTIONS:
            q_id = q["id"]
            
            if q_id in module_responses and not q["is_gate"]:
                ans = module_responses[q_id]

                if 'tooltip' not in q["section"]:
                    display = q["section"]
                else:
                    section = re.search(r'>([^<]+)<', q["section"]).group(1).strip()
                    f = re.search(r"<span[^>]*?>(.*?)</span>", q["section"]).group(1)

                    if not any(f in x for x in footnotes.values()):
                        counter += 1
                    footnotes[section] = "*"*counter + re.search(r"<span[^>]*?>(.*?)</span>", q["section"]).group(1)
                    display = section + "*"*counter

                if q["type"] == "toggle":
                    selected_opts = [opt for idx, opt in enumerate(q["options"].keys()) if idx < len(ans) and ans[idx]]
                    ans_str = "<br/>• ".join(selected_opts) if selected_opts else "None active"
                    if ans_str != "None active": ans_str = "• " + ans_str
                elif q["type"] == "select_all":
                    selected_opts = [opt for opt in ans if opt != "Select one"]
                    ans_str = "<br/>• ".join(selected_opts) if selected_opts else "None active"
                    if ans_str != "None active": ans_str = "• " + ans_str
                elif q["type"] == "single_choice":
                    ans_str = str(ans)
                
                if ans_str != "Select one" and ans_str != "":
                    table_data.append([
                        Paragraph(f"<b>{display}</b><br/>{q['clean_question']}", body_style) if "<div" in q["question"] else Paragraph(f"<b>{display}</b><br/>{q['question']}", body_style),
                        Paragraph(ans_str, body_style),
                        Paragraph(str(calculate_score({q["id"]: ans})), body_style)
                    ])
                    
        if len(table_data) > 1:
            t = Table(table_data, colWidths=[280, 170, 80])
            t.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ]))
            story.append(t)
        else:
            story.append(Paragraph("No active answers recorded for this category.", body_style))

        story.append(Spacer(1,30))
        for v in set(footnotes.values()):
            story.append(Paragraph(v, body_style))
        story.append(PageBreak())
            
    append_breakdown("1. Humanness Index Breakdown", h_resp)
    append_breakdown("2. Relevance Index Breakdown", r_resp)
    append_breakdown("3. NAM Fidelity Index Breakdown", n_resp)
    story.append(Image("images/inetmed_letterhead.png", width = 600, height = 110))

    
    doc.build(story)
    buffer.seek(0)
    input_stream = io.BytesIO(buffer.getvalue())
    reader = PdfReader(input_stream)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)
    
        permissions = (
        UserAccessPermissions.PRINT 
        | UserAccessPermissions.PRINT_TO_REPRESENTATION 
        | ~3
    )

    writer.encrypt(
        user_password="", 
        owner_password="iwhfuwehfpejoie", 
        permissions_flag=int(permissions)
    )
    
    output_stream = io.BytesIO()
    writer.write(output_stream)
    return output_stream.getvalue()

def render_question_group(group_name, responses):
    """
    Renders all questions belonging to one group.
    """

    st.subheader(group_name)

    group_questions = [q for q in QUESTIONS if q["group"] == group_name]

    gate_failed = False

    for q in group_questions:
        st.markdown("""
            <style>
            .tooltip, .definition {
            position: relative;
            display: inline-block;
            border-bottom: 1px dotted #182B49; 
            color: #C69214;
            cursor: pointer;
            }

            .tooltip .tooltiptext, .definition .definitiontext {
            visibility: hidden;
            width: 400px;
            font-size: 0.6em;
            font-weight: 400;
            background-color: #333;
            color: #fff;
            text-align: center;
            border-radius: 6px;
            padding: 8px;
            position: absolute;
            z-index: 1;
            bottom: 125%; 
            left: 50%;
            margin-left: -100px;
            opacity: 0;
            transition: opacity 0.3s;
            }
                    
            .definition .definitiontext {
                font-size: 12px;
            }

            .tooltip:hover .tooltiptext, .definition:hover .definitiontext {
            visibility: visible;
            opacity: 1;
            }
            </style>
            """, unsafe_allow_html=True)
        if q["is_gate"]:
            st.markdown(
                f"""
                <h4>
                    {q["section"]}
                    <span style="
                        margin-left: 20px;
                        background:#FFCD00;
                        color:#C69214;
                        padding:2px 8px;
                        border-radius:12px;
                        font-size:0.7em;
                        font-family: 'Source Code Pro';
                        margin-right:8px;
                    ">Gate</span>
                </h4>
                """,
                unsafe_allow_html=True,
            )
        else:
            
            st.markdown(
                f"#### {q['section']}", 
                unsafe_allow_html=True,
                )
            

        answer_options = ["Select one"] + list(q["options"].keys())

        st.markdown(q["question"], unsafe_allow_html=True)

        if q["type"] == "single_choice":
            selected_answer = st.selectbox(
                label = "",
                options = answer_options,
                key=q["id"],
                disabled=gate_failed if not q["is_gate"] else False,
                label_visibility="collapsed"
            )
        elif q["type"] == "select_all":
            selected_answer = st.multiselect(
                label = "",
                options = answer_options,
                key = q["id"],
                disabled= gate_failed if not q["is_gate"] else False,
                label_visibility="collapsed"
            )
        elif q["type"] == "toggle":
            selected_answer = []
            for o in q["options"]:
                toggle = st.toggle(
                    o,
                    disabled= gate_failed if not q["is_gate"] else False,
                )
                selected_answer.append(toggle)

        if q["is_gate"]:
            gate_failed = selected_answer == "No"



        if selected_answer != "Select one" and not gate_failed:
            if q["type"] == "toggle" and not any(selected_answer):
                selected_points = 0
            elif q["type"] == "select_all" and not selected_answer:
                selected_points = 0
            else:
                selected_points = calculate_score({q["id"]: selected_answer})
                responses[q["id"]] = selected_answer

        else:
            selected_points = 0

        if not q["is_gate"]:
            st.caption(
                f"Current contribution: {selected_points} / {q['max_points']} points"
            )

def process_and_fill_svg(svg_filepath, percentage, color_hex):
    """
    Modifies an SVG so that it fills as a single cohesive unit from the bottom up,
    by using global canvas coordinates (userSpaceOnUse) for the gradient.
    """
    try:
        ET.register_namespace('', "http://www.w3.org/2000/svg")
        
        tree = ET.parse(svg_filepath)
        root = tree.getroot()
        
        color_hex = color_hex.lstrip('#')
        
        # 1. Extract dimensions to define the global height scale
        viewbox = root.get('viewBox')
        if viewbox:
            _, _, vb_w, vb_h = viewbox.split()
            width, height = float(vb_w), float(vb_h)
        else:
            width = float(root.get('width', '500').replace('px', ''))
            height = float(root.get('height', '500').replace('px', ''))

        # 2. Calculate exact absolute Y position where the color changes
        # SVG 0 is the very top, 'height' is the very bottom.
        split_y = height - (height * (percentage / 100))
        
        grad_id = "global_svg_grad"
        
        # 3. Use gradientUnits="userSpaceOnUse" and absolute coordinates (y1 -> y2)
        # This treats the whole SVG canvas as a single shared bucket.
        defs_markup = f"""
        <defs xmlns="http://www.w3.org/2000/svg">
            <linearGradient id="{grad_id}" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="{height}">
                <stop offset="0%" stop-color="#CCCCCC" stop-opacity="0.3" />
                <stop id="split-top" y-pos="{split_y}" offset="{split_y}" stop-color="#CCCCCC" stop-opacity="0.3" />
                <stop id="split-bottom" y-pos="{split_y}" offset="{split_y}" stop-color="#{color_hex}" stop-opacity="1" />
                <stop offset="100%" stop-color="#{color_hex}" stop-opacity="1" />
            </linearGradient>
        </defs>
        """
        
        # ElementTree requires percentages or fractional bounds for string offsets in basic parsers,
        # so we will inject the exact percentage representation of the global split point:
        split_percent = 100 - percentage
        
        defs_markup = f"""
        <defs xmlns="http://www.w3.org/2000/svg">
            <linearGradient id="{grad_id}" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="{height}">
                <stop offset="0%" stop-color="#CCCCCC" stop-opacity="0.3" />
                <stop offset="{split_percent}%" stop-color="#CCCCCC" stop-opacity="0.3" />
                <stop offset="{split_percent}%" stop-color="#{color_hex}" stop-opacity="1" />
                <stop offset="100%" stop-color="#{color_hex}" stop-opacity="1" />
            </linearGradient>
        </defs>
        """
        defs_element = ET.fromstring(defs_markup)
        
        # 4. Clean individual shape styles so they fall back to the parent container's fill rule
        def strip_fills(element):
            if 'fill' in element.attrib:
                del element.attrib['fill']
            if 'style' in element.attrib:
                style = element.attrib['style']
                style = re.sub(r'fill\s*:\s*[^;]+;?', '', style)
                element.attrib['style'] = style
            for child in element:
                strip_fills(child)

        root_children = list(root)
        global_group = ET.Element('g', {
            'id': 'cohesive_fill_group',
            'fill': f"url(#{grad_id})" 
        })
        
        for child in root_children:
            root.remove(child)
            strip_fills(child)
            global_group.append(child)
            
        root.append(defs_element)
        root.append(global_group)
        
        svg_string = ET.tostring(root, encoding='utf-8').decode('utf-8')
        return svg_string, None

    except Exception as e:
        return None, f"Error processing SVG: {str(e)}"

def get_user_id():
    with st.form("my_form"):
        fname = st.text_input("First Name:")
        lname = st.text_input("Last Name:")
        email = st.text_input("Email:")
        institution = st.text_input("Institution:")
        purpose = st.text_area("Purpose of Use:")
        submitted = st.form_submit_button("Submit")

        if submitted:
            user_id = {
                "first name": fname,
                "last name": lname,
                "email": email,
                "institution": institution,
                "purpose": purpose
            }
            return user_id, submitted
        else:
            return {"name": "", "email": "", "institution": "", "purpose": ""}, submitted

def generate_csv_files():
    csv_data = {
        "Humanness": responses,
        "Relevance": r_responses,
        "NAM Fidelity": n_responses
    }
    for module, data in csv_data.items():
        df = pd.DataFrame.from_dict(data, orient='index')
        df.to_csv(f"{module}_responses.csv")

@st.fragment
def show_pdf(pdf_bytes):
    st.pdf(pdf_bytes)

# ============================================================
# App header
# ============================================================

if st.query_params.get("page") != "calculator":
    st.markdown(
        """
        <style>
            .stApp {
                background: #ffffff;
            }

            [data-testid="stHeader"] {
                display: none;
            }

            .block-container {
                max-width: 100%;
                margin: 0;
                padding: 0 0 2rem !important;
            }

            .landing-link {
                display: block;
                width: 100%;
                color: inherit;
                text-decoration: none;
            }

            .landing-link img {
                display: block;
                width: 100%;
                height: auto;
                object-fit: contain;
            }

            .landing-cta {
                padding: 1rem 1.5rem;
                background: #ffffff;
                color: #ffffff;
                font-size: clamp(1.1rem, 2vw, 1.5rem);
                font-weight: 500;
                letter-spacing: 0.01em;
                text-align: center;
            }

            .landing-link:hover .landing-cta {
                background: #0a7f8f;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    landing_image = Path(__file__).resolve().parent / "images" / "website_picture.png"
    landing_image_data = base64.b64encode(landing_image.read_bytes()).decode("ascii")
    st.markdown(
        f'<a class="landing-link" href="?page=calculator" target="_self" '
        f'aria-label="Launch the Humanness calculator">'
        f'<img src="data:image/png;base64,{landing_image_data}" '
        f'alt="TRUST-NAM framework and report card">'
        f'<div class="landing-cta">Click anywhere to launch the calculator</div>'
        f"</a>",
        unsafe_allow_html=True,
    )
    st.stop()

st.title("COMPASS Humanness Calculator")

st.markdown(
    """
    Human-derived does not always mean human-relevant. This platform provides simple, transparent, and interoperable scoring frameworks for evaluating the Humanness, Relevance, and Fidelity of AI/ML-integrated NAMs using cohort-anchored biological evidence. Users can enter study features through a coding-free interface, generate quantitative benchmarking reports, and download publication-ready PDF summaries for reporting, benchmarking, and translational assessment.
    """
)

st.markdown("""
    <style>
        /* Expand the entire tab list to take full width */
        .stTabs [data-baseweb="tab-list"] {
            display: flex;
            width: 100%;
        }
        
        /* Make each tab fill the available width evenly */
        .stTabs [data-baseweb="tab"] {
            flex: 1;
            align-items: center;
            justify-content: center;
            height: 60px; /* Adjust tab height */
            margin: 5px;
        }

        /* Increase font size and text alignment */
        .stTabs [data-baseweb="tab"] p {
            font-size: 20px !important; /* Adjust font size */
            font-weight: 600;
        }
    </style>
""", unsafe_allow_html=True)

hscore, rscore, nscore, download = st.tabs(["Humanness", "Relevance", "NAM Fidelity", "Download Report ⬇"])

with hscore:
    st.markdown(
        "**Humanness Index** — Measures how strongly a discovery or model is anchored in real human biology."
    )
    responses = {}
    render_question_group("Model Training Module", responses)
    st.divider()
    render_question_group("Model Validation Module", responses)
    st.divider()
    render_question_group("Additional Support Module", responses)
    st.divider()
    score = calculate_score(responses)
    st.subheader("Final COMPASS Humanness Score")
    st.metric("Humanness Score", f"{score}%")
    st.progress(int(score))
    st.info(get_interpretation(score))
    st.divider()

    svg_markup, error = process_and_fill_svg(
        "images/human.svg", 
        score, 
        "#FFCD00"         
    )

    if not error and svg_markup:
            # Render the raw vector data perfectly at full crisp scale
            st.image(svg_markup, width='content')

with rscore:
    st.markdown(
        """
        **Relevance Index** — Measures how closely a model connects to clinically meaningful disease states, outcomes, and treatment responses.
        """
    )
    r_responses = {}

    render_question_group("Module Relevance Module", r_responses)
    r_score = calculate_score(r_responses)
    st.subheader("Final COMPASS Relevance Score")

    st.metric("Relevance Score", f"{r_score}%")

    st.progress(int(r_score))

    st.info(get_relevance_interpretation(r_score))

    st.divider()

    svg_markup, error = process_and_fill_svg(
        "images/relevance.svg", 
        r_score, 
        "#FFCD00"          
    )

    if not error and svg_markup:
            # Render the raw vector data perfectly at full crisp scale
            st.image(svg_markup, width='content')

with nscore:
    st.markdown(
        """
        **NAM Fidelity Index** — Measures how faithfully and reproducibly a NAM captures human disease biology in a scalable, fit-for-purpose manner.
        """
    )
    n_responses = {}

    render_question_group("Biological Fidelity", n_responses)
    n_score = calculate_score(n_responses)
    st.subheader("Final COMPASS NAM Fidelity Score")

    st.metric("NAM Fidelity Score", f"{n_score}%")

    st.progress(int(n_score))

    st.divider()

    svg_markup, error = process_and_fill_svg(
        "images/nam.svg", 
        n_score, 
        "#FFCD00"         
    )

    if not error and svg_markup:
            # Render the raw vector data perfectly at full crisp scale
            st.image(svg_markup, width='content')

with download:
    st.header("Generate Assessment Report")
    st.write("Click the button below to parse all recorded parameters and compile an official, publication-ready PDF document." \
    " The report includes a summary of all entered responses, the final Humanness, Relevance, and NAM Fidelity scores, and a detailed breakdown of each module's scoring contributions.")

    st.markdown("**Important:** To view the report you must provide information about yourself (name, email, institution, and purpose of use).")

    # Recalculate up-to-date values across sessions
    final_h = calculate_score(responses)
    final_r = calculate_score(r_responses)
    final_n = calculate_score(n_responses)


    
    # Compile document buffer
    user_id, submitted = get_user_id()

    pdf_bytes = generate_pdf_report(
        responses,
        r_responses,
        n_responses,
        final_h,
        final_r,
        final_n,
        user_id
    )

    show_pdf(pdf_bytes)
    
    st.download_button(
        label="Download Publication PDF Summary ⬇",
        data=pdf_bytes,
        file_name="TRUST_NAM_Humanness_Assessment_Report.pdf",
        mime="application/pdf",
        disabled=not submitted or not user_id.get("name") or not user_id.get("email") or not user_id.get("institution") or not user_id.get("purpose"),
    )

#TO-DO: Only allow download if the user inputs name, email id, institution, and purpose
#Generate csv for us
#Have accounts based on these details
