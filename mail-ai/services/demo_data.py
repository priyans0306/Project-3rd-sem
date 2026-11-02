"""Email text presets for demos; predictions are always produced by the model."""

CATEGORY_PRESETS = {
    "Customer Support": [
        {
            "id": "customer-support-critical",
            "title": "Customer Support: Production Outage",
            "sender": "devops@clientplatform.io",
            "subject": "CRITICAL: Production checkout service returning HTTP 500 internal errors",
            "body": "Customer checkout transactions on the web storefront are failing with 500 internal server errors. Payment gateway webhooks appear stuck. On-call engineering required ASAP."
        },
        {
            "id": "customer-support-password-reset",
            "title": "Customer Support: Password Reset Loop",
            "sender": "helpdesk@northstarretail.com",
            "subject": "Login issue: reset email never arrives after repeated password recovery attempts",
            "body": "Hi team, I have tried resetting my password three times this morning and the reset email never reaches my inbox. I cannot access my order history and need immediate assistance for a shipping delay."
        },
        {
            "id": "customer-support-order-mismatch",
            "title": "Customer Support: Order Status Mismatch",
            "sender": "orders@marketlane.io",
            "subject": "Order #88432 shows delivered but package has not arrived",
            "body": "Our order was marked delivered yesterday, but the tracking status still shows the package in transit and our customer is asking for a refund. Please investigate and provide a clear resolution timeline."
        },
        {
            "id": "customer-support-account-access",
            "title": "Customer Support: Account Access Issue",
            "sender": "customer@harboroutfitters.com",
            "subject": "Login recovery assistance needed for customer account",
            "body": "My password recovery link keeps returning an error and I cannot view my account. Please help me reset the password and restore access."
        },
        {
            "id": "customer-support-missing-delivery",
            "title": "Customer Support: Missing Delivery Status",
            "sender": "service@brightpathhome.com",
            "subject": "Missing delivery status update for my order",
            "body": "My order has not arrived and the tracking page has not changed. Please investigate the delivery and let me know when the package will arrive."
        }
    ],
    "Security": [
        {
            "id": "security-phishing-alert",
            "title": "Security: Suspicious Credential Request",
            "sender": "security-alert@portal-verification.xyz",
            "subject": "CRITICAL: Corporate Mailbox Quota Exceeded - Verify Password Now",
            "body": "Your corporate Office 365 storage has exceeded 99%. To prevent immediate account deactivation, verify your credentials at http://portal-auth-check.xyz/login within 2 hours."
        },
        {
            "id": "security-vpn-cert",
            "title": "Security: VPN Certificate Expired",
            "sender": "it-admin@regionalops.net",
            "subject": "Emergency: remote access certificate expired for finance team VPN",
            "body": "The VPN certificate for the finance remote access gateway expired at 08:00 AM. Users cannot authenticate and need a replacement certificate before the quarterly close process begins."
        },
        {
            "id": "security-iam-approval",
            "title": "Security: Unusual Privilege Request",
            "sender": "identity@enterprisehub.io",
            "subject": "Approval required: temporary admin access request for new contractor account",
            "body": "A contractor account requests temporary elevated permissions for system migration testing. The request was submitted from an unrecognized device and should be reviewed before approval."
        }
    ],
    "Finance": [
        {
            "id": "finance-invoice-dispute",
            "title": "Finance: Consulting Invoice Dispute",
            "sender": "accounting@partnerenterprise.com",
            "subject": "Discrepancy in monthly consulting invoice INV-2026-402",
            "body": "Hi Accounts, we noticed invoice INV-2026-402 bills for 65 hours of external advisory when our signed statement of work capped billable time at 40 hours. Please issue a corrected invoice and revised credit memo."
        },
        {
            "id": "finance-payment-delay",
            "title": "Finance: Vendor Payment Delay",
            "sender": "ap@northbridgevendors.com",
            "subject": "Urgent: payment status request for April invoice batch",
            "body": "We have not received payment for the April invoice batch despite the due date passing two weeks ago. Please confirm the payment schedule and update us on the expected settlement date."
        },
        {
            "id": "finance-expense-approval",
            "title": "Finance: Travel Expense Reimbursement",
            "sender": "director@venturefleet.ai",
            "subject": "Expense report approval needed for executive client travel",
            "body": "Our quarterly travel expense report contains an unusually high volume of airfare and hotel charges tied to a client visit. We need approval and reimbursement before the end of the month close."
        },
        {
            "id": "finance-duplicate-vendor-charge",
            "title": "Finance: Duplicate Vendor Charge",
            "sender": "controller@ridgewaypartners.com",
            "subject": "Duplicate charge found on vendor statement INV-8841",
            "body": "The vendor statement lists invoice INV-8841 twice, resulting in an overpayment of $4,250. Please reconcile the accounts payable ledger and request a credit for the duplicate charge."
        },
        {
            "id": "finance-quarterly-close",
            "title": "Finance: Quarterly Close Reconciliation",
            "sender": "finance.ops@meridianholdings.com",
            "subject": "Open reconciliation items required before quarterly close",
            "body": "Several ledger entries remain unmatched for the quarter, including bank deposits and accrued expenses. Please review the reconciliation workbook and submit corrected balances before close."
        }
    ],
    "Operations": [
        {
            "id": "operations-shipping-delay",
            "title": "Operations: Freight Shipping Delay",
            "sender": "logistics@transoceanic.com",
            "subject": "CRITICAL: Severe shipping delay on international container shipment #MSK-9021",
            "body": "Ocean freight shipment #MSK-9021 carrying critical assembly components has been delayed by 18 days due to port congestion. Immediate alternative air freight sourcing required."
        },
        {
            "id": "operations-power-outage",
            "title": "Operations: Warehouse Power Outage",
            "sender": "facilities@goodsync-ops.com",
            "subject": "Unplanned power outage affecting cold storage distribution line",
            "body": "A local grid issue caused a 5-hour outage in the cold storage facility affecting perishable shipments. Please confirm emergency backup power procedures and reroute inventory immediately."
        },
        {
            "id": "operations-inventory-mismatch",
            "title": "Operations: Inventory Count Mismatch",
            "sender": "warehouse@pivotchain.com",
            "subject": "Inventory variance detected at distribution center DC-07",
            "body": "The quarterly inventory audit shows a 12% variance in high-demand component bins. We need a reconciliation check before the next outbound shipment wave begins."
        },
        {
            "id": "operations-supplier-delivery",
            "title": "Operations: Supplier Delivery Schedule",
            "sender": "dispatch@northlinefreight.com",
            "subject": "Updated delivery window for the weekly parts shipment",
            "body": "The supplier has moved the weekly parts delivery to Thursday morning. Please update the receiving schedule, assign dock staff, and confirm the revised arrival window with the warehouse team."
        }
    ],
    "HR": [
        {
            "id": "hr-parental-leave",
            "title": "HR: Parental Leave Request",
            "sender": "michael.chang@company.org",
            "subject": "Formal parental leave request for upcoming calendar quarter",
            "body": "Dear People Operations, I am writing to formally request 12 weeks of parental leave beginning November 15th. I have prepared a comprehensive handover plan for my team."
        },
        {
            "id": "hr-benefits-enrollment",
            "title": "HR: Benefits Enrollment Deadline",
            "sender": "benefits@peoplefirstgroup.com",
            "subject": "Reminder: medical and dental enrollment deadline is Friday",
            "body": "Employees who have not completed their benefits enrollment by Friday need to update dependent information or select a new plan before the annual enrollment window closes."
        },
        {
            "id": "hr-recruiting-schedule",
            "title": "HR: Candidate Interview Coordination",
            "sender": "talent@northstarjobs.ai",
            "subject": "Interview schedule confirmation for final-stage engineering candidates",
            "body": "Please confirm panel availability for three final-round interviews next week. We need to coordinate room bookings and standardized question packs before the candidate slot confirmations go out."
        }
    ],
    "Sales": [
        {
            "id": "sales-enterprise-demo",
            "title": "Sales: Enterprise Demo Request",
            "sender": "cto@globalcorplogistics.com",
            "subject": "Enterprise sales inquiry: Inbound email triage for 2,500 support agents",
            "body": "Hello, I am the Chief Technology Officer at Global Logistics Corp. We receive over 60,000 customer emails monthly and want to schedule an executive demo of Mail AI."
        },
        {
            "id": "sales-renewal-negotiation",
            "title": "Sales: Renewal Negotiation",
            "sender": "vp-sales@bluepeak.io",
            "subject": "Contract renewal discussion with existing enterprise account",
            "body": "Our current annual contract is due for renewal in 30 days. We want to review pricing, service credits, and the optional AI classification module before the legal team prepares revisions."
        },
        {
            "id": "sales-partner-referral",
            "title": "Sales: Partner Referral Lead",
            "sender": "partners@atlascloud.com",
            "subject": "Referral from system integration partner for healthcare customer expansion",
            "body": "A channel partner shared a warm referral from a healthcare client seeking automated triage and case routing for inbound service requests. Please schedule a discovery call within the next 48 hours."
        },
        {
            "id": "sales-pricing-proposal",
            "title": "Sales: Pricing Proposal Request",
            "sender": "procurement@silveroakhealth.com",
            "subject": "Request for enterprise pricing proposal and product overview",
            "body": "Our procurement team is evaluating email automation platforms for a new customer care program. Please send an enterprise pricing proposal, implementation overview, and available dates for a product demonstration."
        },
        {
            "id": "sales-new-region",
            "title": "Sales: New Region Expansion",
            "sender": "growth@redwoodsystems.io",
            "subject": "Discussion about expanding our subscription into a new region",
            "body": "We are planning to expand our existing subscription to two additional regions next quarter. Please share a quote for the added seats and arrange a call to discuss the commercial terms."
        }
    ],
    "General": [
        {
            "id": "general-facility-notice",
            "title": "General: Campus Facility Notice",
            "sender": "facilities@corporatecampus.net",
            "subject": "Notice: Exterior window washing scheduled for corporate campus buildings",
            "body": "Professional window cleaning contractors will be working on the exterior of building A and B this weekend. Please ensure all window blinds are closed and sills cleared."
        },
        {
            "id": "general-office-move",
            "title": "General: Office Move Coordination",
            "sender": "admin@peaksummit.com",
            "subject": "Building relocation and workspace assignment update for Q4",
            "body": "The east wing office team will relocate to the new innovation lab next month. Please review your updated desk assignments and submit any furniture requests before Friday."
        },
        {
            "id": "general-travel-policy",
            "title": "General: Travel Policy Reminder",
            "sender": "operations@qadigital.io",
            "subject": "Updated travel reimbursement rules for Q4 remote client visits",
            "body": "The travel policy has been updated to include hotel booking caps and meal reimbursement limits for client visits. Please review the revised policy before submitting final travel claims."
        }
    ]
}

if len({len(emails) for emails in CATEGORY_PRESETS.values()}) < 2:
    raise ValueError("Demo presets must be distributed unevenly across categories.")

DEMO_PRESETS = [
    email for category in CATEGORY_PRESETS.values() for email in category
]
