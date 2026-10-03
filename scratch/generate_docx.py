import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn, nsdecls
from docx.parse_xml import parse_xml

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def set_table_borders(table, color="D0D7DE"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
        f'  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="{color}"/>'
        f'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
        f'  <w:insideV w:val="none"/>'
        f'  <w:left w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def add_callout(doc, text, bold_prefix=""):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Inches(6.0)
    
    cell = table.cell(0, 0)
    set_cell_background(cell, "F0F4F8")
    set_cell_margins(cell, top=120, bottom=120, left=200, right=200)
    
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'  <w:left w:val="single" w:sz="24" w:space="0" w:color="0071BC"/>'
        f'  <w:top w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'  <w:bottom w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r_b = p.add_run(bold_prefix)
        r_b.bold = True
        r_b.font.name = "Calibri"
        r_b.font.size = Pt(10)
        r_b.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)
    r_t = p.add_run(text)
    r_t.font.name = "Calibri"
    r_t.font.size = Pt(10)
    r_t.font.italic = True
    r_t.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    
    # spacing after table
    sp_p = doc.add_paragraph()
    sp_p.paragraph_format.space_before = Pt(0)
    sp_p.paragraph_format.space_after = Pt(4)

def add_code_box(doc, lines):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Inches(6.0)
    
    cell = table.cell(0, 0)
    set_cell_background(cell, "F6F8FA")
    set_cell_margins(cell, top=140, bottom=140, left=180, right=180)
    
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'  <w:left w:val="single" w:sz="6" w:space="0" w:color="D0D7DE"/>'
        f'  <w:top w:val="single" w:sz="6" w:space="0" w:color="D0D7DE"/>'
        f'  <w:right w:val="single" w:sz="6" w:space="0" w:color="D0D7DE"/>'
        f'  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="D0D7DE"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.05
    for i, line in enumerate(lines):
        if i > 0:
            p = cell.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.05
        r = p.add_run(line)
        r.font.name = "Consolas"
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(0x24, 0x29, 0x2E)
        
    sp_p = doc.add_paragraph()
    sp_p.paragraph_format.space_before = Pt(0)
    sp_p.paragraph_format.space_after = Pt(6)

def format_run_tokens(paragraph, text, base_font="Calibri", base_size=11):
    import re
    # parse markdown inline bold **text** and code `text`
    tokens = re.split(r'(\*\*[^*]+\*\*|`[^`]+`)', text)
    for token in tokens:
        if not token:
            continue
        if token.startswith('**') and token.endswith('**'):
            r = paragraph.add_run(token[2:-2])
            r.bold = True
            r.font.name = base_font
            r.font.size = Pt(base_size)
            r.font.color.rgb = RGBColor(0x20, 0x20, 0x20)
        elif token.startswith('`') and token.endswith('`'):
            r = paragraph.add_run(token[1:-1])
            r.font.name = "Consolas"
            r.font.size = Pt(base_size - 1)
            r.font.color.rgb = RGBColor(0xA3, 0x15, 0x15)
        else:
            r = paragraph.add_run(token)
            r.font.name = base_font
            r.font.size = Pt(base_size)
            r.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

def add_heading_1(doc, text):
    h = doc.add_heading(level=1)
    h.paragraph_format.space_before = Pt(14)
    h.paragraph_format.space_after = Pt(6)
    h.paragraph_format.keep_with_next = True
    r = h.add_run(text)
    r.font.name = "Calibri"
    r.font.size = Pt(18)
    r.font.bold = True
    r.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)
    return h

def add_heading_2(doc, text):
    h = doc.add_heading(level=2)
    h.paragraph_format.space_before = Pt(12)
    h.paragraph_format.space_after = Pt(4)
    h.paragraph_format.keep_with_next = True
    r = h.add_run(text)
    r.font.name = "Calibri"
    r.font.size = Pt(14)
    r.font.bold = True
    r.font.color.rgb = RGBColor(0x20, 0x54, 0x93)
    return h

def add_heading_3(doc, text):
    h = doc.add_heading(level=3)
    h.paragraph_format.space_before = Pt(10)
    h.paragraph_format.space_after = Pt(3)
    h.paragraph_format.keep_with_next = True
    r = h.add_run(text)
    r.font.name = "Calibri"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = RGBColor(0x00, 0x71, 0xBC)
    return h

def add_body_p(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    format_run_tokens(p, text)
    return p

def add_bullet_p(doc, text, level=0):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    if level > 0:
        p.paragraph_format.left_indent = Inches(0.25 * (level + 1))
    format_run_tokens(p, text)
    return p

def add_number_p(doc, num_str, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.left_indent = Inches(0.25)
    r_num = p.add_run(num_str + " ")
    r_num.bold = True
    r_num.font.name = "Calibri"
    r_num.font.size = Pt(11)
    r_num.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)
    format_run_tokens(p, text)
    return p

def generate_document():
    doc = Document()
    
    # Configure 1-inch margins
    for sec in doc.sections:
        sec.top_margin = Inches(1.0)
        sec.bottom_margin = Inches(1.0)
        sec.left_margin = Inches(1.0)
        sec.right_margin = Inches(1.0)
        sec.page_width = Inches(8.5)
        sec.page_height = Inches(11.0)
        
    # --- 4.3 Architectural Design ---
    add_heading_1(doc, "4.3 Architectural Design")
    
    # --- 4.3.1 Software Architectural Design ---
    add_heading_2(doc, "4.3.1 Software Architectural Design")
    
    add_heading_3(doc, "Architecture Overview")
    add_body_p(doc, "VALORA's target software architecture is a modular, domain-driven, layered system. It is explicitly **not** a Model-View-Controller (MVC) architecture. Instead, VALORA follows a Clean Architecture-inspired pattern in which concerns are separated into distinct, inward-pointing layers: the frontend handles presentation, the API layer handles HTTP routing and security, service classes implement business use cases, repositories abstract data access, and the domain layer contains the core business entities.")
    add_body_p(doc, "This architecture is specifically designed to support VALORA's central product concept: connecting community operational data with property financial intelligence through an analytics layer, so that community health directly informs property valuation.")
    
    add_callout(doc, 
                "The technology stack (React frontend, FastAPI backend, SQLAlchemy repositories, PostgreSQL persistence) validates that this architectural pattern is technically feasible and already directionally established. Implementation details are referenced below only to establish feasibility, not to constrain the target design.",
                "Current implementation alignment: ")
    
    add_heading_3(doc, "Architectural Layers")
    add_body_p(doc, "The software is organized into the following strict layers, with dependencies pointing inward:")
    add_number_p(doc, "1.", "**Presentation Layer (Frontend):** React-based Single Page Application (SPA) providing persona-specific views (Resident, HOA, Investor).")
    add_number_p(doc, "2.", "**API Layer:** FastAPI routers that handle HTTP requests, perform input validation via Pydantic schemas, and enforce Role-Based Access Control (RBAC) via JWTs.")
    add_number_p(doc, "3.", "**Application/Service Layer:** Orchestrates business use cases (e.g., auth lifecycle, complaint routing, Living Score calculation) and coordinates between domain models and persistence.")
    add_number_p(doc, "4.", "**Repository/Data-Access Layer:** Abstracts database interactions using asynchronous SQLAlchemy, ensuring the service layer remains decoupled from SQL specifics.")
    add_number_p(doc, "5.", "**Domain/Model Layer:** The core business entities (User, Property, Complaint, LivingScore, AIAnalytic) that define the system's structure.")
    add_number_p(doc, "6.", "**Infrastructure Layer:** External concerns such as the PostgreSQL database and ML model execution context.")
    
    add_heading_3(doc, "Core Software Components")
    add_bullet_p(doc, "**Frontend Application:** Built with React and Vite.")
    add_bullet_p(doc, "**FastAPI Backend:** The core monolith, subdivided into domain-driven modules:")
    add_bullet_p(doc, "`Identity Module`: Authentication and user management.", level=1)
    add_bullet_p(doc, "`Property Module`: Estate and unit management.", level=1)
    add_bullet_p(doc, "`Community Module`: Complaints, announcements, and maintenance work orders.", level=1)
    add_bullet_p(doc, "`Providers Module`: Service provider registry and reviews.", level=1)
    add_bullet_p(doc, "`Analytics Module`: Translates community operational data (complaint frequency, maintenance resolution times, provider ratings) into the Living Score and property valuation insights. The Living Score entity and data schema are established; the scoring and ML inference services are planned for implementation.", level=1)
    add_bullet_p(doc, "**Persistence:** Relational PostgreSQL database managed via Alembic migrations.")
    
    add_heading_3(doc, "Component Responsibilities")
    add_bullet_p(doc, "**API Layer:** Terminates HTTP connections, translates JSON payloads to internal schemas, and guards endpoints.")
    add_bullet_p(doc, "**Service Layer:** Implements the proprietary logic connecting community health (unresolved complaints, maintenance times) to property health (Living Score).")
    add_bullet_p(doc, "**Analytics Component:** Consumes community operational data to output financial and livability intelligence.")
    
    add_heading_3(doc, "Dependency Flow")
    add_body_p(doc, "Control flows from the User → Presentation Layer → HTTP/REST API Layer → Service Layer → Repository Layer → Infrastructure/Database.")
    
    add_heading_3(doc, "Architectural Rationale")
    add_body_p(doc, "The layered architecture ensures that the complex logic calculating property intelligence is entirely decoupled from how data is delivered (HTTP) or stored (SQL). The domain-driven module structure prevents the system from splitting into two disconnected applications (property listing vs. complaint management), enforcing a unified \"Property Health\" model.")
    
    # --- 4.3.2 Hardware Architectural Design ---
    add_heading_2(doc, "4.3.2 Hardware Architectural Design")
    
    add_heading_3(doc, "Target Deployment Architecture")
    add_body_p(doc, "VALORA's target hardware architecture is a cloud-hosted, containerized deployment that separates client devices from application compute and data persistence, with an ingress layer handling public traffic.")
    
    diag_lines = [
        "Users (Web Browsers / Mobile Browsers)",
        "          ↓ HTTPS",
        "     Internet / Public Network",
        "          ↓",
        "  Load Balancer / Ingress",
        "          ↓",
        "  Application Compute",
        "  ├── Frontend Service  (React/Vite SPA served via CDN or container)",
        "  └── API Service       (FastAPI/Uvicorn)",
        "          ↓",
        "  Managed Relational Database  (PostgreSQL)",
        "          +",
        "  Object Storage               (Property images, complaint attachments)"
    ]
    add_code_box(doc, diag_lines)
    
    add_heading_3(doc, "Infrastructure Nodes")
    
    table_data = [
        ("Node", "Role", "Target Technology"),
        ("Client Device", "Web browser rendering the SPA", "Any modern browser"),
        ("Load Balancer / Ingress", "Routes public HTTPS traffic to services", "Cloud-managed LB (provider-agnostic)"),
        ("Frontend Service", "Serves the React SPA", "Container or CDN-hosted static build"),
        ("API Service", "Executes FastAPI application logic", "Python 3.10+ container"),
        ("Database", "Relational persistence, ACID guarantees", "PostgreSQL (managed service)"),
        ("Object Storage", "Binary asset storage", "Cloud object storage")
    ]
    
    table = doc.add_table(rows=len(table_data), cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table)
    
    col_widths = [Inches(1.8), Inches(2.6), Inches(2.1)]
    
    for row_idx, row in enumerate(table_data):
        for col_idx, text in enumerate(row):
            cell = table.cell(row_idx, col_idx)
            cell.width = col_widths[col_idx]
            set_cell_margins(cell, top=80, bottom=80, left=120, right=120)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.05
            
            if row_idx == 0:
                set_cell_background(cell, "1B365D")
                r = p.add_run(text)
                r.bold = True
                r.font.name = "Calibri"
                r.font.size = Pt(10)
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            else:
                if row_idx % 2 == 1:
                    set_cell_background(cell, "FFFFFF")
                else:
                    set_cell_background(cell, "F9FAFB")
                r = p.add_run(text)
                r.font.name = "Calibri"
                r.font.size = Pt(9.5)
                r.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
                if col_idx == 0:
                    r.bold = True
                    
    sp_tbl = doc.add_paragraph()
    sp_tbl.paragraph_format.space_before = Pt(2)
    sp_tbl.paragraph_format.space_after = Pt(4)
    
    add_body_p(doc, "The choice of cloud provider (AWS, Azure, GCP) is not architecturally significant and is deferred to the deployment planning phase. The containerized packaging ensures portability across providers without changes to application code.")
    
    add_heading_3(doc, "Infrastructure Responsibilities")
    add_bullet_p(doc, "**Client:** Renders the SPA; holds only ephemeral session state (JWT in memory/localStorage).")
    add_bullet_p(doc, "**Load Balancer:** Terminates TLS, distributes requests, provides a single public entry point.")
    add_bullet_p(doc, "**API Compute:** Executes all business logic, authentication, and data processing. Stateless — can be horizontally scaled.")
    add_bullet_p(doc, "**Database:** Sole source of persistent domain state. Not exposed to the public network.")
    add_bullet_p(doc, "**Object Storage:** Stores binary assets referenced by property listings and complaint records.")
    
    add_heading_3(doc, "Current Implementation Alignment")
    add_body_p(doc, "The current local development environment uses Docker Compose to mirror this architecture on a single machine:")
    add_bullet_p(doc, "`valora_frontend` container (port 4173) → corresponds to Frontend Service")
    add_bullet_p(doc, "`valora_api` container (port 8000) → corresponds to API Service")
    add_bullet_p(doc, "`valora_db` container (port 5432, PostgreSQL 15) → corresponds to Managed Database")
    add_bullet_p(doc, "`postgres_data` Docker volume → corresponds to persistent storage")
    add_body_p(doc, "This establishes feasibility and ensures environment parity across development machines. The load balancer and object storage nodes are not present in local development; they are production-only concerns.")
    
    add_heading_3(doc, "Deployment Rationale")
    add_body_p(doc, "Separating compute from persistence allows each tier to be scaled independently. Placing the database on a private internal network (not exposed to the public internet) is the primary security mechanism protecting raw domain data. Object storage decouples binary asset management from the relational database and API, preserving database performance.")
    
    # --- 4.3.3 Network Architectural Design ---
    add_heading_2(doc, "4.3.3 Network Architectural Design")
    
    add_heading_3(doc, "Network Overview")
    add_body_p(doc, "The network architecture defines communication paths between the decoupled frontend and backend, as well as internal container networking. It relies on standard web protocols and establishes clear security trust boundaries.")
    
    add_heading_3(doc, "Communication Paths")
    add_number_p(doc, "1.", "**User to Frontend:** User interactions occur entirely within the client's browser after the initial asset load.")
    add_number_p(doc, "2.", "**Frontend to API (Backend):** The React client communicates with the FastAPI backend via asynchronous REST API calls over HTTP(S).")
    add_number_p(doc, "3.", "**API to Database:** The FastAPI backend communicates with the PostgreSQL database container over a dedicated internal Docker network.")
    
    add_heading_3(doc, "Security Boundaries")
    add_bullet_p(doc, "**External Trust Boundary (Untrusted to Trusted):** The connection between the public Internet (Client) and the API. This boundary is secured by:")
    add_bullet_p(doc, "JWT (JSON Web Token) bearer authentication for endpoint authorization.", level=1)
    add_bullet_p(doc, "(Proposed) TLS/HTTPS encryption for data in transit.", level=1)
    add_bullet_p(doc, "**Internal Trust Boundary (Trusted to Trusted):** The connection between the API container and the Database container.")
    add_bullet_p(doc, "The database port (5432) is heavily restricted and should not be exposed to the public internet in production.", level=1)
    add_bullet_p(doc, "Communication relies on secure connection strings and internal network routing.", level=1)
    
    add_heading_3(doc, "Protocols")
    add_bullet_p(doc, "**External:** HTTP / HTTPS (REST/JSON).")
    add_bullet_p(doc, "**Internal:** TCP/IP (AsyncPG database driver protocol).")
    
    add_heading_3(doc, "Network Rationale")
    add_body_p(doc, "The separation of the frontend and API over REST ensures the backend acts as a strict, secure boundary for all business rules and data access. Keeping the database on a private, unexposed network segment protects raw domain data from direct external attack.")
    
    # --- 4.3.4 Class Diagram ---
    add_heading_2(doc, "4.3.4 Class Diagram")
    
    add_heading_3(doc, "Core Classes")
    add_bullet_p(doc, "**User:** Base class for all system personas (Resident, Admin, Investor, Agent).")
    add_bullet_p(doc, "**Property:** Represents a physical real estate unit.")
    add_bullet_p(doc, "**Complaint:** An operational issue reported by a resident affecting community health.")
    add_bullet_p(doc, "**MaintenanceWorkOrder:** The operational response to a complaint, involving a service provider.")
    add_bullet_p(doc, "**ServiceProvider:** Third-party contractor assigned to resolve issues.")
    add_bullet_p(doc, "**AIAnalytic / LivingScoreEntity:** The intelligence layer quantifying the property's health.")
    
    add_heading_3(doc, "Attributes (Key Examples)")
    add_bullet_p(doc, "**User:** `user_id`, `email`, `role`, `hoa_approved`")
    add_bullet_p(doc, "**Property:** `unit_id`, `unit_no`, `complex_name`")
    add_bullet_p(doc, "**Complaint:** `complaint_id`, `category`, `status`, `is_anonymous`")
    add_bullet_p(doc, "**MaintenanceWorkOrder:** `work_order_id`, `status`, `job_cost`, `resident_rating`")
    add_bullet_p(doc, "**ServiceProvider:** `provider_id`, `trade`, `avg_rating`, `verified`")
    add_bullet_p(doc, "**AIAnalytic:** `analytics_id`, `predicted_market_value`, `growth_score`, `confidence_score`")
    
    add_heading_3(doc, "Relationships & Multiplicity")
    add_bullet_p(doc, "**User to Complaint (Association):** A User (Resident) logs zero or more Complaints. (1 to 0..*)")
    add_bullet_p(doc, "**Property to Complaint (Association):** A Property is the subject of zero or more Complaints. (1 to 0..*)")
    add_bullet_p(doc, "**Complaint to MaintenanceWorkOrder (Association):** A Complaint may trigger zero or one Work Order. (1 to 0..1)")
    add_bullet_p(doc, "**ServiceProvider to MaintenanceWorkOrder (Association):** A Service Provider executes zero or more Work Orders. (1 to 0..*)")
    add_bullet_p(doc, "**Property to AIAnalytic (Composition):** A Property has generated intelligence/analytics derived from its operational history. (1 to 0..*)")
    
    add_heading_3(doc, "Responsibilities")
    add_body_p(doc, "The class structure explicitly links operational events to financial outcomes. `Complaint` and `MaintenanceWorkOrder` track the real-time health of the community. `AIAnalytic` is responsible for ingesting this operational history (alongside traditional property data) to generate the Living Score and valuation metrics, fulfilling the system's core product mandate.")
    
    add_heading_3(doc, "Class Diagram Specification")
    add_body_p(doc, "The entities are derived directly from the SQLAlchemy ORM models implemented in the repository, ensuring complete fidelity to the actual database schema and application domain logic.")
    
    # --- Diagram Generation Specification ---
    add_heading_1(doc, "Diagram Generation Specification")
    add_body_p(doc, "This section provides precise instructions for creating the four corresponding Draw.io architectural visualisations.")
    
    # Diagram 1
    add_heading_2(doc, "Diagram 1: 01_VALORA_Software_Architecture")
    add_bullet_p(doc, "**Purpose:** Show the layered, domain-driven structure (NOT MVC) and the dependency flow from UI to Database.")
    add_bullet_p(doc, "**Nodes/Containers:**")
    add_bullet_p(doc, "*Presentation Layer:* React Frontend SPA", level=1)
    add_bullet_p(doc, "*API Layer:* FastAPI Routers, JWT Auth Guard", level=1)
    add_bullet_p(doc, "*Application/Service Layer (Grouped):* AuthService, PropertyService, CommunityService, Analytics/LivingScore Engine", level=1)
    add_bullet_p(doc, "*Repository Layer:* SQLAlchemy Repositories", level=1)
    add_bullet_p(doc, "*Domain Layer:* Core Entities (User, Property, Complaint, etc.)", level=1)
    add_bullet_p(doc, "*Infrastructure Layer:* PostgreSQL Database", level=1)
    add_bullet_p(doc, "**Relationships:** Top-down directed arrows. Presentation -> API -> Service -> Repository -> Domain. Repository -> Infrastructure.")
    add_bullet_p(doc, "**Labels:** Label arrows with actions (e.g., \"HTTP/JSON\", \"Calls\", \"Queries\").")
    add_bullet_p(doc, "**MUST NOT Include:** Cloud provider logos, load balancers, or MVC terminology (Model/View/Controller).")
    
    # Diagram 2
    add_heading_2(doc, "Diagram 2: 02_VALORA_Hardware_Architecture")
    add_bullet_p(doc, "**Purpose:** Illustrate the currently IMPLEMENTED containerized local deployment using Docker.")
    add_bullet_p(doc, "**Nodes/Containers:**")
    add_bullet_p(doc, "*Client Device:* Web Browser", level=1)
    add_bullet_p(doc, "*Docker Host (Local Machine):* (Large container box)", level=1)
    add_bullet_p(doc, "Node 1: `valora_frontend` Container (Port 4173)", level=2)
    add_bullet_p(doc, "Node 2: `valora_api` Container (Port 8000)", level=2)
    add_bullet_p(doc, "Node 3: `valora_db` Container (Port 5432)", level=2)
    add_bullet_p(doc, "Node 4: `postgres_data` Docker Volume", level=2)
    add_bullet_p(doc, "**Relationships:** Client -> valora_frontend. valora_frontend -> valora_api. valora_api -> valora_db. valora_db -> postgres_data (Volume mount).")
    add_bullet_p(doc, "**Labels:** Use Docker logos or container icons. Label \"IMPLEMENTED Architecture\".")
    add_bullet_p(doc, "**MUST NOT Include:** AWS/Azure/GCP specific services (EC2, S3, RDS), as they are proposed, not implemented.")
    
    # Diagram 3
    add_heading_2(doc, "Diagram 3: 03_VALORA_Network_Architecture")
    add_bullet_p(doc, "**Purpose:** Define communication protocols and security boundaries.")
    add_bullet_p(doc, "**Nodes/Containers:** Internet / Public Network, Client Browser, Frontend Application, FastAPI Backend, PostgreSQL Database.")
    add_bullet_p(doc, "**Security Boundaries:**")
    add_bullet_p(doc, "Draw a dashed line box around Frontend & Client labeled \"Untrusted Zone\".", level=1)
    add_bullet_p(doc, "Draw a solid line box around API and Database labeled \"Trusted Internal Network\".", level=1)
    add_bullet_p(doc, "**Relationships/Protocols:**")
    add_bullet_p(doc, "Client -> Frontend (HTTPS/HTTP)", level=1)
    add_bullet_p(doc, "Frontend -> API (REST API / JSON / JWT Auth)", level=1)
    add_bullet_p(doc, "API -> Database (TCP/IP / AsyncPG)", level=1)
    add_bullet_p(doc, "**MUST NOT Include:** Hardware specs or internal code layers (like Repositories). Focus strictly on nodes and protocols over the wire.")
    
    # Diagram 4
    add_heading_2(doc, "Diagram 4: 04_VALORA_Class_Diagram")
    add_bullet_p(doc, "**Purpose:** Detail the core domain models and how community operations link to property analytics.")
    add_bullet_p(doc, "**Nodes (UML Classes):**")
    add_bullet_p(doc, "`User`: user_id, email, role, full_name", level=1)
    add_bullet_p(doc, "`Property`: unit_id, unit_no, complex_name", level=1)
    add_bullet_p(doc, "`Complaint`: complaint_id, category, status", level=1)
    add_bullet_p(doc, "`MaintenanceWorkOrder`: work_order_id, status, job_cost", level=1)
    add_bullet_p(doc, "`ServiceProvider`: provider_id, trade, avg_rating", level=1)
    add_bullet_p(doc, "`AIAnalytic`: analytics_id, predicted_market_value, growth_score", level=1)
    add_bullet_p(doc, "**Relationships (with Direction and Multiplicity):**")
    add_bullet_p(doc, "User -> Complaint (Association, 1 to 0..*)", level=1)
    add_bullet_p(doc, "Property -> Complaint (Association, 1 to 0..*)", level=1)
    add_bullet_p(doc, "Complaint -> MaintenanceWorkOrder (Association, 1 to 0..1)", level=1)
    add_bullet_p(doc, "ServiceProvider -> MaintenanceWorkOrder (Association, 1 to 0..*)", level=1)
    add_bullet_p(doc, "Property -> AIAnalytic (Composition/Strong Association, 1 to 0..*)", level=1)
    add_bullet_p(doc, "**Labels:** Standard UML notation. Focus on attributes; no methods strictly required unless identifying a service action.")
    add_bullet_p(doc, "**MUST NOT Include:** Every single database table (like linking tables) or infrastructure classes (like routers or database sessions). Keep it strictly focused on the business domain.")
    
    # Save to both paths
    paths = [
        "Valora_Architectural_Design.docx",
        os.path.join("docs", "Valora_Architectural_Design.docx")
    ]
    
    for path in paths:
        doc.save(path)
        print(f"Successfully saved to {path}")

if __name__ == "__main__":
    generate_document()
