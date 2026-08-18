# VALORA Frontend Development Prompt

## 1. Overview
**VALORA** is an AI-powered Property Health Intelligence Platform. It bridges the gap between property valuation and community management, proving that a well-managed estate increases property value. The frontend must clearly visualize this connection: **Community Operations → Community Health → Living Score → Investment Intelligence**.

## 2. Design & Aesthetics
* **Theme & Vibe:** Trustworthy, modern, premium, and data-driven. The design should balance the analytical nature of a financial tool with the user-friendliness of a community app.
* **Color Palette:** Professional tones. Deep blues or greens (symbolizing wealth, health, and growth) with crisp, clean white/light gray backgrounds for readability. 
* **Typography:** Clean, modern sans-serif fonts optimized for data readability and clear visual hierarchy.
* **Data Visualization:** Use clear, intuitive charts, progress bars, and gauges, particularly for the **Living Score (0-100)**, so users can instantly grasp a property's health at a glance. Micro-interactions and smooth hover states are essential for a premium feel.

## 3. Core Layouts & Views (MVP)

The frontend must adapt based on the authenticated user's role:

### A. Landing Page (Casual Visitor)
* **Goal:** Lead generation and conveying the core value proposition.
* **Layout:**
  * Clean hero section: *"Know more than what a property costs. Know why it's worth it."*
  * Search Bar: Allow users to search an address or suburb to get a free valuation estimate.
  * Call to Action (CTA): Prompt visitors to sign up to unlock the full "Living Score" and in-depth ROI insights.

### B. Resident Dashboard
* **Goal:** Easy reporting and transparency on community health.
* **Layout:**
  * **Top Summary:** Quick view of their property details and the estate's current **Living Score**.
  * **Quick Actions:** Prominent, frictionless "Log a Complaint" button.
  * **My Complaints:** A kanban or status list view tracking the lifecycle of their complaints (Logged → Under Review → Assigned → In Progress → Resolved → Closed).
  * **Community Feed:** Recent HOA announcements and general estate updates.

### C. HOA Admin Dashboard
* **Goal:** Efficient community management and score improvement.
* **Layout:**
  * **Overview Metrics:** Average resolution time, complaint frequency, and the live Living Score.
  * **Complaint Management Pipeline:** Interactive dashboard to view, approve, and assign complaints to service providers.
  * **Service Provider Directory:** Interface to view, verify, and assign tasks to service providers.
  * **Announcements:** Form to publish updates to all residents.

### D. Investor Dashboard
* **Goal:** Data-driven decision-making.
* **Layout:**
  * **Property Search & Profile:** Detailed view of properties including the AI-powered valuation.
  * **Living Score Breakdown:** A visual breakdown of the score (Resolution Time, Complaint Frequency, Security, Satisfaction, Maintenance) showing how it is calculated.
  * **Trend Analysis:** Read-only charts showing complaint trends and historical estate performance.
  * **ROI Projections:** Simple visual representation of 10-year ROI and rental yield estimates.

## 4. Backend Integration & API Interaction
To work seamlessly with the backend, the frontend must handle the following interactions:

* **Authentication & Authorization:** Secure login routing users to their respective role-based dashboards (Resident, Investor, HOA Admin, etc.).
* **Forms & Data Submission:**
  * Fast, responsive complaint submission with category tags (Resident).
  * Work order status updates and assignment (HOA Admin / Service Provider).
  * Feedback and rating submissions upon complaint resolution (Resident).
* **Dynamic Data Rendering:** 
  * Fetching the dynamic 90-day rolling **Living Score** and visualizing the data points securely.
  * Real-time or smoothly polled status updates for complaints and maintenance work orders.
* **AI & Metrics Display:** Consuming AI valuation endpoints and rendering complex data (Living Score breakdowns, normalizations, and benchmarks) simply and elegantly. AI recommendations must be explainable.

## 5. Key UX Success Criteria
* **Transparency:** The relationship between a resolved complaint and the Living Score must be visually obvious to users.
* **Frictionless Action:** Logging a complaint or assigning a work order should take less than 3 clicks. No unnecessary forms.
* **Explainability:** When the AI provides a valuation or Living Score, users should easily be able to click or hover to see *why* the score is what it is (e.g., "Score dropped due to 3 recent security incidents").
