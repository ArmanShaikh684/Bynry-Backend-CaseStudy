# StockFlow B2B SaaS - Backend Engineering Case Study

**Candidate:** Arman Shaikh  
**Role:** Backend Engineering Intern  

This repository contains my submission for the StockFlow Backend Engineering case study. My solution is broken down into three main parts: a code review of an existing API endpoint, a scalable database schema design, and the implementation of a new low-stock alerting feature.

---

## Part 1: Code Review & Debugging (Part1_Solution.py)

In the first part of the assessment, I reviewed an existing API endpoint for creating products and identified several critical issues that could impact business operations:

*   **Non-Atomic Database Operations:** The original code committed the product creation before attempting to create the inventory record. If the inventory insertion failed, the database would be left in an inconsistent state, breaking downstream logic. Both operations must succeed or fail together.
*   **Missing Input Validation & Error Handling:** The code accessed data blindly without verifying if required fields existed or if their data types were valid. This would lead to application crashes and unhandled server errors instead of helpful feedback for the user.
*   **No SKU Uniqueness Handling:** Despite the requirement for unique SKUs, the database commit lacked proper error handling for duplicate entries. Submitting an existing SKU would result in a server error rather than a clear conflict response.
*   **Incorrect HTTP Status Codes:** The endpoint defaulted to returning a `200 OK` status, whereas returning `201 Created` is the standard for RESTful API creation endpoints. Adhering to standards makes the API more predictable for clients.

**My Corrected Implementation (`Part1_Solution.py`):**
I rewrote the endpoint to address these issues. The new implementation includes robust input validation, wraps database operations in a single atomic transaction context using `db.session.flush()`, gracefully handles `IntegrityError` for duplicate SKUs, and returns the appropriate HTTP status codes.

---

## Part 2: Database Design (Part2_Database_Design.sql)

For the database schema, I designed a structure tailored for a B2B SaaS environment, utilizing PostgreSQL. 

### Key Design Decisions & Justifications:

*   **Multi-Tenancy Isolation:** Every core table links back to a `company_id`. This is critical for ensuring data isolation between different tenants. For example, two different companies can use the same SKU internally, but cross-company data remains completely separated (enforced by `UNIQUE(company_id, sku)`).
*   **Audit Ledger (`inventory_transactions`):** Instead of simply updating a quantity number in the `inventory` table, every change writes a new row to an immutable transaction ledger. This historical record is essential for calculating sales velocity, tracking down missing stock, and building future analytics.
*   **Cascading Deletes:** I applied cascading deletes selectively (`ON DELETE CASCADE`) so that if a company leaves the platform, their associated data is cleaned up efficiently without leaving orphaned records behind.
*   **Performance Indexing:** Indexes were added on frequently queried columns (`product_id` in inventory, `inventory_id` and `created_at` in transactions) to ensure API endpoints remain performant as the data grows.

### Questions for Product/Business (Missing Requirements):
While designing the schema, a few questions came up that I would typically clarify with the product team:
*   **SKU Scope:** Should SKUs be strictly unique across the entire platform, or just unique per company? (I assumed per company for a better user experience).
*   **Bundle Logistics:** Do we track the physical inventory of pre-assembled bundles, or does selling a bundle simply deduct the inventory of its component parts dynamically?
*   **Multi-Supplier Items:** Can a single product be sourced from multiple suppliers? The current design assumes a 1-to-1 relationship for simplicity, though enterprise supply chains often involve multiple vendors.
*   **Sales Velocity Definition:** What exactly defines "recent sales activity" when determining if a product is dead stock? (e.g., any sale in the last 30 days, or a specific velocity rate?).

---

## Part 3: API Implementation (Part3_API_Implementation.py)

The final part of the case study involves an endpoint (`/api/companies/<uuid:company_id>/alerts/low-stock`) that calculates low-stock alerts. It queries the inventory, checks for recent sales via the transaction ledger to filter out "dead stock," and calculates an estimated stockout date.

### Edge Cases Handled:

*   **Tenant Data Leaks:** The database query explicitly filters by the company's ID (`Product.company_id == company_id`), guaranteeing that users cannot manipulate the URL path to view another company's alerts.
*   **Dead Stock / Division by Zero:** If a product's inventory drops below the alert threshold but it hasn't sold recently, the logic skips it. This prevents division-by-zero errors when calculating the remaining days until stockout and reduces "alert fatigue" for abandoned products.
*   **Missing Suppliers:** I used an outer join (`outerjoin(Supplier)`) for the supplier data. If a product doesn't have a supplier assigned yet, the code gracefully handles the missing data without throwing errors and returns `None` for the supplier info.