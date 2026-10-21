"""Email text presets for demos; predictions are always produced by the model."""

DEMO_PRESETS = [
    {
        "id": "customer_support",
        "title": "Customer Support: Production Outage",
        "sender": "devops@clientplatform.io",
        "subject": "CRITICAL: Production checkout service returning HTTP 500 internal errors",
        "body": "Customer checkout transactions on the web storefront are failing with 500 internal server errors. Payment gateway webhooks appear stuck. On-call engineering required ASAP."
    },
    {
        "id": "security_threat",
        "title": "Security: Suspicious Credential Request",
        "sender": "security-alert@portal-verification.xyz",
        "subject": "CRITICAL: Corporate Mailbox Quota Exceeded - Verify Password Now",
        "body": "Your corporate Office 365 storage has exceeded 99%. To prevent immediate account deactivation, verify your credentials at http://portal-auth-check.xyz/login within 2 hours."
    },
    {
        "id": "finance_discrepancy",
        "title": "Finance: Consulting Invoice Dispute",
        "sender": "accounting@partnerenterprise.com",
        "subject": "Discrepancy in monthly consulting invoice INV-2026-402",
        "body": "Hi Accounts, we noticed invoice INV-2026-402 bills for 65 hours of external advisory when our signed statement of work capped billable time at 40 hours. Please issue a corrected invoice and revised credit memo."
    },
    {
        "id": "operations_shipping",
        "title": "Operations: Freight Shipping Delay",
        "sender": "logistics@transoceanic.com",
        "subject": "CRITICAL: Severe shipping delay on international container shipment #MSK-9021",
        "body": "Ocean freight shipment #MSK-9021 carrying critical assembly components has been delayed by 18 days due to port congestion. Immediate alternative air freight sourcing required."
    },
    {
        "id": "hr_policy",
        "title": "HR: Parental Leave Request",
        "sender": "michael.chang@company.org",
        "subject": "Formal parental leave request for upcoming calendar quarter",
        "body": "Dear People Operations, I am writing to formally request 12 weeks of parental leave beginning November 15th. I have prepared a comprehensive handover plan for my team."
    },
    {
        "id": "sales_enterprise",
        "title": "Sales: Enterprise Demo Request",
        "sender": "cto@globalcorplogistics.com",
        "subject": "Enterprise sales inquiry: Inbound email triage for 2,500 support agents",
        "body": "Hello, I am the Chief Technology Officer at Global Logistics Corp. We receive over 60,000 customer emails monthly and want to schedule an executive demo of Mail AI."
    },
    {
        "id": "general_routine",
        "title": "General: Campus Facility Notice",
        "sender": "facilities@corporatecampus.net",
        "subject": "Notice: Exterior window washing scheduled for corporate campus buildings",
        "body": "Professional window cleaning contractors will be working on the exterior of building A and B this weekend. Please ensure all window blinds are closed and sills cleared."
    }
]
