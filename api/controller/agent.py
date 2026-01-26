from api.models.agent import ChatHistory
from api.models.agent import ChatSessionList
from api.agent.memory import ChatMemory
from uuid import UUID
from api.repository.utils import get_schema_name
from api.controller.company import get_company_schema
from api.repository.utils import set_search_path
from api.models.agent import ExecuteQueryRequest
from api.dependencies import DatabasePoolDep
from typing import Annotated
from fastapi import Query
from fastapi import Depends
from api.models.agent import AgentResponse
from api.models.agent import AgentRequest
from fastapi import APIRouter
from api.agent.orchestrator import SalesAgentOrchestrator
from api.settings.settings import Settings,get_settings
import structlog
logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/agents",
    tags=["Agents"],
    responses={
        400: {"description": "Bad Request - Invalid input or hierarchy"},
        404: {"description": "Resource Not Found"},
        500: {"description": "Internal Server Error"},
    },
)

table_schema_dict = {
    "salesforce.users": {
        "description": "Stores user information including authentication and company association",
        "columns": {
            "id": {"type": "UUID", "description": "Primary key, auto-generated UUID", "nullable": False},
            "username": {"type": "VARCHAR(32)", "description": "Username for authentication", "nullable": True},
            "name": {"type": "VARCHAR(64)", "description": "Full name of the user", "nullable": False},
            "contact_no": {"type": "VARCHAR(15)", "description": "Contact number of the user", "nullable": False},
            "company_id": {"type": "UUID", "description": "Foreign key to company table", "nullable": True},
            "is_super_admin": {"type": "BOOLEAN", "description": "Flag to indicate if user is super admin", "nullable": False, "default": False},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if user is active", "nullable": False, "default": True},
            "created_at": {"type": "TIMESTAMP", "description": "Timestamp when record was created", "nullable": False, "default": "now()"},
            "updated_at": {"type": "TIMESTAMP", "description": "Timestamp when record was last updated", "nullable": False, "default": "now()"}
        },
        "constraints": [
            "PRIMARY KEY (id)",
            "UNIQUE (username)",
            "UNIQUE (contact_no, company_id) WHERE is_active = true",
            "FOREIGN KEY (company_id) REFERENCES company(id)"
        ],
        "indexes": ["idx_users_company_id ON company_id"]
    },
    "salesforce.company": {
        "description": "Stores company information and registration details",
        "columns": {
            "id": {"type": "UUID", "description": "Primary key, auto-generated UUID", "nullable": False},
            "name": {"type": "VARCHAR(255)", "description": "Name of the company", "nullable": False},
            "gst_no": {"type": "VARCHAR(15)", "description": "GST registration number", "nullable": False},
            "cin_no": {"type": "VARCHAR(21)", "description": "CIN registration number", "nullable": False},
            "address": {"type": "TEXT", "description": "Physical address of the company", "nullable": False},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if company is active", "nullable": False, "default": True},
            "created_at": {"type": "TIMESTAMP", "description": "Timestamp when record was created", "nullable": False, "default": "now()"},
            "updated_at": {"type": "TIMESTAMP", "description": "Timestamp when record was last updated", "nullable": False, "default": "now()"}
        },
        "constraints": [
            "PRIMARY KEY (id)",
            "UNIQUE (gst_no) WHERE is_active = true",
            "UNIQUE (cin_no) WHERE is_active = true"
        ]
    },
    "roles": {
        "description": "Stores role definitions and their permissions",
        "columns": {
            "name": {"type": "VARCHAR(32)", "description": "Primary key, name of the role", "nullable": False},
            "description": {"type": "TEXT", "description": "Description of the role", "nullable": True},
            "permissions": {"type": "VARCHAR(64)[]", "description": "Array of permissions for the role", "nullable": False, "default": "{}"},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if role is active", "nullable": False, "default": True},
            "created_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was created", "nullable": False, "default": "CURRENT_TIMESTAMP"},
            "updated_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was last updated", "nullable": False, "default": "CURRENT_TIMESTAMP"}
        },
        "constraints": ["PRIMARY KEY (name)"]
    },
    "areas": {
        "description": "Stores hierarchical area information (Nation, Zone, Region, Area)",
        "columns": {
            "id": {"type": "SERIAL", "description": "Primary key, auto-incremented", "nullable": False},
            "name": {"type": "VARCHAR(64)", "description": "Name of the area", "nullable": False},
            "type": {"type": "VARCHAR(32)", "description": "Type of area (NATION/ZONE/REGION/AREA)", "nullable": False},
            "area_id": {"type": "INT", "description": "Foreign key to parent area", "nullable": True},
            "region_id": {"type": "INT", "description": "Foreign key to region", "nullable": True},
            "zone_id": {"type": "INT", "description": "Foreign key to zone", "nullable": True},
            "nation_id": {"type": "INT", "description": "Foreign key to nation", "nullable": True},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if area is active", "nullable": False, "default": True},
            "created_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was created", "nullable": False, "default": "CURRENT_TIMESTAMP"},
            "updated_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was last updated", "nullable": False, "default": "CURRENT_TIMESTAMP"}
        },
        "constraints": [
            "PRIMARY KEY (id)",
            "UNIQUE (name, type) WHERE is_active = true",
            "FOREIGN KEY (area_id) REFERENCES areas(id)",
            "FOREIGN KEY (region_id) REFERENCES areas(id)",
            "FOREIGN KEY (zone_id) REFERENCES areas(id)",
            "FOREIGN KEY (nation_id) REFERENCES areas(id)"
        ]
    },
    "members": {
        "description": "Stores company members with their roles and assigned areas",
        "columns": {
            "id": {"type": "UUID", "description": "Primary key, references users table", "nullable": False},
            "role": {"type": "VARCHAR(32)", "description": "Foreign key to roles table", "nullable": True},
            "area_id": {"type": "INT", "description": "Foreign key to areas table", "nullable": True},
            "bank_details": {"type": "JSONB", "description": "Bank account details in JSON format", "nullable": True},
            "salary": {"type": "INTEGER", "description": "Salary of the member", "nullable": False, "default": 0},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if member is active", "nullable": False, "default": True},
            "created_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was created", "nullable": False, "default": "CURRENT_TIMESTAMP"},
            "updated_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was last updated", "nullable": False, "default": "CURRENT_TIMESTAMP"}
        },
        "constraints": [
            "PRIMARY KEY (id)",
            "FOREIGN KEY (id) REFERENCES salesforce.users(id)",
            "FOREIGN KEY (role) REFERENCES roles(name)",
            "FOREIGN KEY (area_id) REFERENCES areas(id)"
        ],
        "indexes": ["idx_members_area_id ON area_id", "idx_members_role ON role"]
    },
    "routes": {
        "description": "Stores route information for different shop types",
        "columns": {
            "id": {"type": "SERIAL", "description": "Primary key, auto-incremented", "nullable": False},
            "name": {"type": "VARCHAR(32)", "description": "Name of the route", "nullable": False},
            "code": {"type": "VARCHAR(32)", "description": "Unique code for the route", "nullable": False},
            "area_id": {"type": "INTEGER", "description": "Foreign key to areas table", "nullable": False},
            "is_general": {"type": "BOOLEAN", "description": "Flag for general shops", "nullable": False},
            "is_modern": {"type": "BOOLEAN", "description": "Flag for modern shops", "nullable": False},
            "is_horeca": {"type": "BOOLEAN", "description": "Flag for HORECA (Hotel/Restaurant/Cafe)", "nullable": False},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if route is active", "nullable": False, "default": True},
            "created_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was created", "nullable": False, "default": "CURRENT_TIMESTAMP"},
            "updated_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was last updated", "nullable": False, "default": "CURRENT_TIMESTAMP"}
        },
        "constraints": [
            "PRIMARY KEY (id)",
            "UNIQUE (code)",
            "FOREIGN KEY (area_id) REFERENCES areas(id)"
        ],
        "indexes": ["idx_routes_area_id ON area_id WHERE is_active = true"]
    },
    "route_assignment": {
        "description": "Stores assignments of routes to members with validity periods",
        "columns": {
            "id": {"type": "SERIAL", "description": "Primary key, auto-incremented", "nullable": False},
            "route_id": {"type": "INTEGER", "description": "Foreign key to routes table", "nullable": False},
            "user_id": {"type": "UUID", "description": "Foreign key to members table", "nullable": False},
            "from_date": {"type": "DATE", "description": "Start date of assignment", "nullable": False},
            "to_date": {"type": "DATE", "description": "End date of assignment", "nullable": True},
            "day": {"type": "INTEGER", "description": "Day of week (0-6)", "nullable": False},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if assignment is active", "nullable": False, "default": True},
            "created_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was created", "nullable": False, "default": "CURRENT_TIMESTAMP"},
            "updated_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was last updated", "nullable": False, "default": "CURRENT_TIMESTAMP"}
        },
        "constraints": [
            "PRIMARY KEY (id)",
            "UNIQUE (route_id, user_id) WHERE is_active = true",
            "FOREIGN KEY (route_id) REFERENCES routes(id)",
            "FOREIGN KEY (user_id) REFERENCES members(id)",
            "CHECK (to_date IS NULL OR to_date >= from_date)",
            "CHECK (day >= 0 AND day <= 6)"
        ]
    },
    "route_logs": {
        "description": "Stores daily logs of route execution by members",
        "columns": {
            "id": {"type": "SERIAL", "description": "Primary key, auto-incremented", "nullable": False},
            "route_assignment_id": {"type": "INT", "description": "Foreign key to route_assignment table", "nullable": False},
            "co_worker_id": {"type": "UUID", "description": "Foreign key to members table for co-worker", "nullable": True},
            "date": {"type": "DATE", "description": "Date of route execution", "nullable": False},
            "start_time": {"type": "TIME", "description": "Start time of route execution", "nullable": False},
            "end_time": {"type": "TIME", "description": "End time of route execution", "nullable": True},
            "created_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was created", "nullable": False, "default": "CURRENT_TIMESTAMP"},
            "updated_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was last updated", "nullable": False, "default": "CURRENT_TIMESTAMP"}
        },
        "constraints": [
            "PRIMARY KEY (id)",
            "FOREIGN KEY (route_assignment_id) REFERENCES route_assignment(id)",
            "FOREIGN KEY (co_worker_id) REFERENCES members(id)",
            "CHECK (end_time IS NULL OR end_time > start_time)"
        ],
        "indexes": ["idx_route_logs_route_assignment_id ON route_assignment_id"]
    },
    "shop_categories": {
        "description": "Stores categories for retail shops",
        "columns": {
            "id": {"type": "SERIAL", "description": "Primary key, auto-incremented", "nullable": False},
            "name": {"type": "VARCHAR(32)", "description": "Name of the shop category", "nullable": False},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if category is active", "nullable": False, "default": True},
            "created_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was created", "nullable": False, "default": "CURRENT_TIMESTAMP"},
            "updated_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was last updated", "nullable": False, "default": "CURRENT_TIMESTAMP"}
        },
        "constraints": ["PRIMARY KEY (id)"]
    },
    "retailer": {
        "description": "Stores retailer/shop information with registration details",
        "columns": {
            "id": {"type": "UUID", "description": "Primary key, auto-generated UUID", "nullable": False},
            "name": {"type": "VARCHAR(255)", "description": "Name of the retailer", "nullable": False},
            "code": {"type": "VARCHAR(255)", "description": "Unique code for the retailer", "nullable": False},
            "contact_person_name": {"type": "VARCHAR(255)", "description": "Name of contact person", "nullable": False},
            "mobile_number": {"type": "VARCHAR(15)", "description": "Mobile number", "nullable": False},
            "email": {"type": "VARCHAR(255)", "description": "Email address", "nullable": True},
            "gst_no": {"type": "VARCHAR(15)", "description": "GST registration number", "nullable": False},
            "pan_no": {"type": "VARCHAR(10)", "description": "PAN card number", "nullable": False},
            "license_no": {"type": "VARCHAR(255)", "description": "License number", "nullable": True},
            "address": {"type": "TEXT", "description": "Physical address", "nullable": False},
            "category_id": {"type": "INTEGER", "description": "Foreign key to shop_categories table", "nullable": False},
            "pin_code": {"type": "VARCHAR(6)", "description": "PIN code", "nullable": False},
            "map_link": {"type": "TEXT", "description": "Google Maps link", "nullable": True},
            "documents": {"type": "JSONB", "description": "Documents in JSON format", "nullable": True},
            "store_images": {"type": "JSONB", "description": "Store images in JSON format", "nullable": True},
            "route_id": {"type": "INTEGER", "description": "Foreign key to routes table", "nullable": False},
            "is_type_a": {"type": "BOOLEAN", "description": "Flag for Type A classification", "nullable": False, "default": False},
            "is_type_b": {"type": "BOOLEAN", "description": "Flag for Type B classification", "nullable": False, "default": False},
            "is_type_c": {"type": "BOOLEAN", "description": "Flag for Type C classification", "nullable": False, "default": False},
            "is_verified": {"type": "BOOLEAN", "description": "Verification status", "nullable": False, "default": False},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if retailer is active", "nullable": False, "default": True},
            "created_at": {"type": "TIMESTAMP", "description": "Timestamp when record was created", "nullable": False, "default": "now()"},
            "updated_at": {"type": "TIMESTAMP", "description": "Timestamp when record was last updated", "nullable": False, "default": "now()"}
        },
        "constraints": [
            "PRIMARY KEY (id)",
            "UNIQUE (code)",
            "UNIQUE (gst_no)",
            "UNIQUE (pan_no)",
            "UNIQUE (license_no)",
            "UNIQUE (mobile_number)",
            "UNIQUE (email)",
            "FOREIGN KEY (category_id) REFERENCES shop_categories(id)",
            "FOREIGN KEY (route_id) REFERENCES routes(id)"
        ]
    },
    "distributor": {
        "description": "Stores distributor information with logistics details",
        "columns": {
            "id": {"type": "UUID", "description": "Primary key, auto-generated UUID", "nullable": False},
            "name": {"type": "VARCHAR(255)", "description": "Name of the distributor", "nullable": False},
            "code": {"type": "VARCHAR(255)", "description": "Unique code for the distributor", "nullable": False},
            "contact_person_name": {"type": "VARCHAR(255)", "description": "Name of contact person", "nullable": False},
            "mobile_number": {"type": "VARCHAR(15)", "description": "Mobile number", "nullable": False},
            "email": {"type": "VARCHAR(255)", "description": "Email address", "nullable": True},
            "gst_no": {"type": "VARCHAR(15)", "description": "GST registration number", "nullable": False},
            "pan_no": {"type": "VARCHAR(10)", "description": "PAN card number", "nullable": False},
            "license_no": {"type": "VARCHAR(255)", "description": "License number", "nullable": True},
            "address": {"type": "TEXT", "description": "Physical address", "nullable": False},
            "pin_code": {"type": "VARCHAR(6)", "description": "PIN code", "nullable": False},
            "map_link": {"type": "TEXT", "description": "Google Maps link", "nullable": True},
            "documents": {"type": "JSONB", "description": "Documents in JSON format", "nullable": True},
            "store_images": {"type": "JSONB", "description": "Store images in JSON format", "nullable": True},
            "vehicle_3": {"type": "INTEGER", "description": "Number of 3-wheeler vehicles", "nullable": False},
            "vehicle_4": {"type": "INTEGER", "description": "Number of 4-wheeler vehicles", "nullable": False},
            "salesman_count": {"type": "INTEGER", "description": "Number of salesmen", "nullable": False},
            "area_id": {"type": "INTEGER", "description": "Foreign key to areas table", "nullable": False},
            "for_general": {"type": "BOOLEAN", "description": "Services general shops", "nullable": False, "default": False},
            "for_modern": {"type": "BOOLEAN", "description": "Services modern shops", "nullable": False, "default": False},
            "for_horeca": {"type": "BOOLEAN", "description": "Services HORECA", "nullable": False, "default": False},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if distributor is active", "nullable": False, "default": True},
            "created_at": {"type": "TIMESTAMP", "description": "Timestamp when record was created", "nullable": False, "default": "now()"},
            "updated_at": {"type": "TIMESTAMP", "description": "Timestamp when record was last updated", "nullable": False, "default": "now()"}
        },
        "constraints": [
            "PRIMARY KEY (id)",
            "UNIQUE (code)",
            "UNIQUE (gst_no)",
            "UNIQUE (pan_no)",
            "UNIQUE (license_no)",
            "UNIQUE (mobile_number)",
            "UNIQUE (email)",
            "FOREIGN KEY (area_id) REFERENCES areas(id)"
        ]
    },
    "distributor_routes": {
        "description": "Many-to-many relationship between distributors and routes",
        "columns": {
            "distributor_id": {"type": "UUID", "description": "Foreign key to distributor table", "nullable": False},
            "route_id": {"type": "INTEGER", "description": "Foreign key to routes table", "nullable": False},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if assignment is active", "nullable": False, "default": True},
            "created_at": {"type": "TIMESTAMP", "description": "Timestamp when record was created", "nullable": False, "default": "now()"},
            "updated_at": {"type": "TIMESTAMP", "description": "Timestamp when record was last updated", "nullable": False, "default": "now()"}
        },
        "constraints": [
            "PRIMARY KEY (distributor_id, route_id, is_active)",
            "FOREIGN KEY (distributor_id) REFERENCES distributor(id)",
            "FOREIGN KEY (route_id) REFERENCES routes(id)"
        ],
        "indexes": ["idx_distributor_routes_distributor_id ON distributor_id", "idx_distributor_routes_route_id ON route_id"]
    },
    "brand": {
        "description": "Stores brand information with channel flags",
        "columns": {
            "id": {"type": "SERIAL", "description": "Primary key, auto-incremented", "nullable": False},
            "name": {"type": "VARCHAR(255)", "description": "Name of the brand", "nullable": False},
            "code": {"type": "VARCHAR(16)", "description": "Unique code for the brand", "nullable": False},
            "for_general": {"type": "BOOLEAN", "description": "Available for general shops", "nullable": False, "default": False},
            "for_modern": {"type": "BOOLEAN", "description": "Available for modern shops", "nullable": False, "default": False},
            "for_horeca": {"type": "BOOLEAN", "description": "Available for HORECA", "nullable": False, "default": False},
            "logo": {"type": "JSONB", "description": "Brand logo in JSON format", "nullable": True},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if brand is active", "nullable": False, "default": True},
            "is_deleted": {"type": "BOOLEAN", "description": "Soft delete flag", "nullable": False, "default": False},
            "created_at": {"type": "TIMESTAMP", "description": "Timestamp when record was created", "nullable": False, "default": "NOW()"},
            "updated_at": {"type": "TIMESTAMP", "description": "Timestamp when record was last updated", "nullable": False, "default": "NOW()"}
        },
        "constraints": [
            "PRIMARY KEY (id)",
            "UNIQUE (code)",
            "UNIQUE (name) WHERE is_active = TRUE AND is_deleted = FALSE"
        ]
    },
    "brand_visibility": {
        "description": "Controls brand visibility by area",
        "columns": {
            "id": {"type": "SERIAL", "description": "Primary key, auto-incremented", "nullable": False},
            "brand_id": {"type": "INT", "description": "Foreign key to brand table", "nullable": False},
            "area_id": {"type": "INT", "description": "Foreign key to areas table", "nullable": True},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if visibility is active", "nullable": False, "default": True},
            "created_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was created", "nullable": False, "default": "CURRENT_TIMESTAMP"},
            "updated_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was last updated", "nullable": False, "default": "CURRENT_TIMESTAMP"}
        },
        "constraints": [
            "PRIMARY KEY (id)",
            "UNIQUE (brand_id, area_id) WHERE is_active = TRUE",
            "FOREIGN KEY (brand_id) REFERENCES brand(id)",
            "FOREIGN KEY (area_id) REFERENCES areas(id)"
        ]
    },
    "brand_margins": {
        "description": "Stores profit margins for brands by area",
        "columns": {
            "id": {"type": "SERIAL", "description": "Primary key, auto-incremented", "nullable": False},
            "name": {"type": "VARCHAR(255)", "description": "Name of the margin configuration", "nullable": False},
            "brand_id": {"type": "INT", "description": "Foreign key to brand table", "nullable": False},
            "area_id": {"type": "INT", "description": "Foreign key to areas table", "nullable": True},
            "margins": {"type": "JSONB", "description": "Margin details in JSON format", "nullable": True},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if margin is active", "nullable": False, "default": True},
            "created_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was created", "nullable": False, "default": "CURRENT_TIMESTAMP"},
            "updated_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was last updated", "nullable": False, "default": "CURRENT_TIMESTAMP"}
        },
        "constraints": [
            "PRIMARY KEY (id)",
            "UNIQUE (brand_id, area_id, is_active)",
            "UNIQUE (brand_id, area_id) WHERE is_active = TRUE",
            "FOREIGN KEY (brand_id) REFERENCES brand(id)",
            "FOREIGN KEY (area_id) REFERENCES areas(id)"
        ]
    },
    "brand_categories": {
        "description": "Stores brand categories with hierarchical support",
        "columns": {
            "id": {"type": "SERIAL", "description": "Primary key, auto-incremented", "nullable": False},
            "name": {"type": "VARCHAR(255)", "description": "Name of the category", "nullable": False},
            "code": {"type": "VARCHAR(16)", "description": "Unique code for the category", "nullable": False},
            "for_general": {"type": "BOOLEAN", "description": "Available for general shops", "nullable": False, "default": False},
            "for_modern": {"type": "BOOLEAN", "description": "Available for modern shops", "nullable": False, "default": False},
            "for_horeca": {"type": "BOOLEAN", "description": "Available for HORECA", "nullable": False, "default": False},
            "logo": {"type": "JSONB", "description": "Category logo in JSON format", "nullable": True},
            "brand_id": {"type": "INT", "description": "Foreign key to brand table", "nullable": False},
            "parent_category_id": {"type": "INT", "description": "Foreign key to parent category (self-referencing)", "nullable": True},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if category is active", "nullable": False, "default": True},
            "is_deleted": {"type": "BOOLEAN", "description": "Soft delete flag", "nullable": False, "default": False},
            "created_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was created", "nullable": False, "default": "CURRENT_TIMESTAMP"},
            "updated_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was last updated", "nullable": False, "default": "CURRENT_TIMESTAMP"}
        },
        "constraints": [
            "PRIMARY KEY (id)",
            "UNIQUE (code)",
            "FOREIGN KEY (brand_id) REFERENCES brand(id)",
            "FOREIGN KEY (parent_category_id) REFERENCES brand_categories(id)"
        ]
    },
    "brand_category_visibility": {
        "description": "Controls brand category visibility by area",
        "columns": {
            "id": {"type": "SERIAL", "description": "Primary key, auto-incremented", "nullable": False},
            "brand_category_id": {"type": "INT", "description": "Foreign key to brand_categories table", "nullable": True},
            "area_id": {"type": "INT", "description": "Foreign key to areas table", "nullable": True},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if visibility is active", "nullable": False, "default": True},
            "created_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was created", "nullable": False, "default": "CURRENT_TIMESTAMP"},
            "updated_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was last updated", "nullable": False, "default": "CURRENT_TIMESTAMP"}
        },
        "constraints": [
            "PRIMARY KEY (id)",
            "UNIQUE (brand_category_id, area_id) WHERE is_active = TRUE",
            "FOREIGN KEY (brand_category_id) REFERENCES brand_categories(id)",
            "FOREIGN KEY (area_id) REFERENCES areas(id)"
        ]
    },
    "brand_category_margins": {
        "description": "Stores profit margins for brand categories by area",
        "columns": {
            "id": {"type": "SERIAL", "description": "Primary key, auto-incremented", "nullable": False},
            "name": {"type": "VARCHAR(255)", "description": "Name of the margin configuration", "nullable": False},
            "brand_category_id": {"type": "INT", "description": "Foreign key to brand_categories table", "nullable": True},
            "area_id": {"type": "INT", "description": "Foreign key to areas table", "nullable": True},
            "margins": {"type": "JSONB", "description": "Margin details in JSON format", "nullable": True},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if margin is active", "nullable": False, "default": True},
            "created_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was created", "nullable": False, "default": "CURRENT_TIMESTAMP"},
            "updated_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was last updated", "nullable": False, "default": "CURRENT_TIMESTAMP"}
        },
        "constraints": [
            "PRIMARY KEY (id)",
            "UNIQUE (brand_category_id, area_id, is_active)",
            "UNIQUE (brand_category_id, area_id) WHERE is_active = TRUE",
            "FOREIGN KEY (brand_category_id) REFERENCES brand_categories(id)",
            "FOREIGN KEY (area_id) REFERENCES areas(id)"
        ]
    },
    "products": {
        "description": "Stores product information with brand and category associations",
        "columns": {
            "id": {"type": "SERIAL", "description": "Primary key, auto-incremented", "nullable": False},
            "brand_id": {"type": "INT", "description": "Foreign key to brand table", "nullable": False},
            "brand_category_id": {"type": "INT", "description": "Foreign key to brand_categories table", "nullable": False},
            "brand_subcategory_id": {"type": "INT", "description": "Foreign key to brand_categories table for subcategory", "nullable": True},
            "name": {"type": "VARCHAR(255)", "description": "Name of the product", "nullable": False},
            "code": {"type": "VARCHAR(100)", "description": "Unique code for the product", "nullable": False},
            "description": {"type": "TEXT", "description": "Product description", "nullable": True},
            "barcode": {"type": "VARCHAR(100)", "description": "Product barcode", "nullable": True},
            "hsn_code": {"type": "VARCHAR(8)", "description": "HSN code for taxation", "nullable": True},
            "gst_rate": {"type": "NUMERIC(5,2)", "description": "GST rate percentage", "nullable": False},
            "gst_category": {"type": "VARCHAR(100)", "description": "GST category", "nullable": False},
            "dimensions": {"type": "JSONB", "description": "Product dimensions in JSON format", "nullable": True},
            "compliance": {"type": "TEXT", "description": "Compliance information", "nullable": True},
            "measurement_details": {"type": "JSONB", "description": "Measurement details in JSON format", "nullable": True},
            "packaging_type": {"type": "VARCHAR(100)", "description": "Type of packaging", "nullable": True},
            "packaging_details": {"type": "JSONB", "description": "Packaging details in JSON format", "nullable": True},
            "images": {"type": "JSONB", "description": "Product images in JSON format", "nullable": True},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if product is active", "nullable": False, "default": True},
            "created_at": {"type": "TIMESTAMP WITH TIME ZONE", "description": "Timestamp when record was created", "nullable": False, "default": "NOW()"},
            "updated_at": {"type": "TIMESTAMP WITH TIME ZONE", "description": "Timestamp when record was last updated", "nullable": False, "default": "NOW()"}
        },
        "constraints": [
            "PRIMARY KEY (id)",
            "UNIQUE (code) WHERE is_active = TRUE",
            "FOREIGN KEY (brand_id) REFERENCES brand(id)",
            "FOREIGN KEY (brand_category_id) REFERENCES brand_categories(id)",
            "FOREIGN KEY (brand_subcategory_id) REFERENCES brand_categories(id)",
            "CHECK (gst_rate >= 0 AND gst_rate <= 28)"
        ],
        "indexes": ["idx_products_brand_id ON brand_id", "idx_products_brand_category_id ON brand_category_id", "idx_products_brand_subcategory_id ON brand_subcategory_id"]
    },
    "product_prices": {
        "description": "Stores product pricing information by area",
        "columns": {
            "id": {"type": "SERIAL", "description": "Primary key, auto-incremented", "nullable": False},
            "product_id": {"type": "INT", "description": "Foreign key to products table", "nullable": False},
            "area_id": {"type": "INT", "description": "Foreign key to areas table", "nullable": True},
            "mrp": {"type": "NUMERIC(10,2)", "description": "Maximum Retail Price", "nullable": False},
            "margins": {"type": "JSONB", "description": "Margin details in JSON format", "nullable": True},
            "min_order_quantity": {"type": "JSONB", "description": "Minimum order quantity in JSON format", "nullable": True},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if price is active", "nullable": False, "default": True},
            "created_at": {"type": "TIMESTAMP WITH TIME ZONE", "description": "Timestamp when record was created", "nullable": False, "default": "NOW()"},
            "updated_at": {"type": "TIMESTAMP WITH TIME ZONE", "description": "Timestamp when record was last updated", "nullable": False, "default": "NOW()"}
        },
        "constraints": [
            "PRIMARY KEY (id)",
            "UNIQUE (product_id, area_id) WHERE is_active = TRUE",
            "FOREIGN KEY (product_id) REFERENCES products(id)",
            "FOREIGN KEY (area_id) REFERENCES areas(id)",
            "CHECK (mrp >= 0)"
        ]
    },
    "product_visibility": {
        "description": "Controls product visibility by area and shop types",
        "columns": {
            "id": {"type": "SERIAL", "description": "Primary key, auto-incremented", "nullable": False},
            "product_id": {"type": "INT", "description": "Foreign key to products table", "nullable": False},
            "area_id": {"type": "INT", "description": "Foreign key to areas table", "nullable": True},
            "for_general": {"type": "BOOLEAN", "description": "Visible for general shops", "nullable": False, "default": False},
            "for_modern": {"type": "BOOLEAN", "description": "Visible for modern shops", "nullable": False, "default": False},
            "for_horeca": {"type": "BOOLEAN", "description": "Visible for HORECA", "nullable": False, "default": False},
            "for_type_a": {"type": "BOOLEAN", "description": "Visible for Type A retailers", "nullable": False, "default": False},
            "for_type_b": {"type": "BOOLEAN", "description": "Visible for Type B retailers", "nullable": False, "default": False},
            "for_type_c": {"type": "BOOLEAN", "description": "Visible for Type C retailers", "nullable": False, "default": False},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if visibility is active", "nullable": False, "default": True},
            "created_at": {"type": "TIMESTAMP WITH TIME ZONE", "description": "Timestamp when record was created", "nullable": False, "default": "NOW()"},
            "updated_at": {"type": "TIMESTAMP WITH TIME ZONE", "description": "Timestamp when record was last updated", "nullable": False, "default": "NOW()"}
        },
        "constraints": [
            "PRIMARY KEY (id)",
            "UNIQUE (product_id, area_id)",
            "FOREIGN KEY (product_id) REFERENCES products(id)",
            "FOREIGN KEY (area_id) REFERENCES areas(id)"
        ]
    },
    "orders": {
        "description": "Stores order information with tax details",
        "columns": {
            "id": {"type": "UUID", "description": "Primary key, auto-generated UUID", "nullable": False},
            "retailer_id": {"type": "UUID", "description": "Foreign key to retailer table", "nullable": False},
            "member_id": {"type": "UUID", "description": "Foreign key to members table", "nullable": False},
            "base_amount": {"type": "NUMERIC", "description": "Base amount before discount", "nullable": False},
            "discount_amount": {"type": "NUMERIC", "description": "Total discount amount", "nullable": False},
            "net_amount": {"type": "NUMERIC", "description": "Amount after discount", "nullable": False},
            "igst_amount": {"type": "NUMERIC", "description": "Integrated GST amount", "nullable": False},
            "cgst_amount": {"type": "NUMERIC", "description": "Central GST amount", "nullable": False},
            "sgst_amount": {"type": "NUMERIC", "description": "State GST amount", "nullable": False},
            "total_amount": {"type": "NUMERIC", "description": "Final total amount", "nullable": False},
            "order_type": {"type": "VARCHAR(16)", "description": "Type of order", "nullable": False},
            "order_status": {"type": "VARCHAR(16)", "description": "Status of order", "nullable": False},
            "is_active": {"type": "BOOLEAN", "description": "Flag to indicate if order is active", "nullable": False, "default": True},
            "created_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was created", "nullable": False, "default": "NOW()"},
            "updated_at": {"type": "TIMESTAMPTZ", "description": "Timestamp when record was last updated", "nullable": False, "default": "NOW()"}
        },
        "constraints": [
            "PRIMARY KEY (id)",
            "FOREIGN KEY (retailer_id) REFERENCES retailer(id)",
            "FOREIGN KEY (member_id) REFERENCES members(id)",
            "CHECK (base_amount >= 0 AND discount_amount >= 0 AND net_amount <= base_amount AND igst_amount >= 0 AND cgst_amount >= 0 AND sgst_amount >= 0 AND total_amount >= net_amount)"
        ],
        "indexes": ["idx_orders_retailer_id ON retailer_id", "idx_orders_member_id ON member_id"]
    },
    "order_items": {
        "description": "Stores individual items in orders",
        "columns": {
            "order_id": {"type": "UUID", "description": "Foreign key to orders table", "nullable": False},
            "product_id": {"type": "INT", "description": "Foreign key to products table", "nullable": False},
            "quantity": {"type": "INT", "description": "Quantity of product ordered", "nullable": False}
        },
        "constraints": [
            "PRIMARY KEY (order_id, product_id)",
            "FOREIGN KEY (order_id) REFERENCES orders(id)",
            "FOREIGN KEY (product_id) REFERENCES products(id)",
            "CHECK (quantity > 0)"
        ]
    }
}

@router.get("/{user_id}/chat")
async def get_chat(user_id: UUID,config: Settings = Depends(get_settings)):
    """Endpoint to retrieve chat history for a user."""
    orchestrator = ChatMemory(backend=config.AGENT.MEMORY_BACKEND, table_name=config.AGENT.TABLE_NAME,region=config.AWS.region_name)
    chat_history = await orchestrator.get_user_sessions(user_id)
    return  ChatSessionList(sessions=chat_history)

@router.get("/{user_id}/chat/{session_id}")
async def get_chat_session(user_id: UUID, session_id: str,config: Settings = Depends(get_settings)):
    """Endpoint to retrieve a specific chat session for a user."""
    orchestrator = ChatMemory(backend=config.AGENT.MEMORY_BACKEND, table_name=config.AGENT.TABLE_NAME,region=config.AWS.region_name)
    chat_session = await orchestrator.get_history(session_id)
    return ChatHistory(items=[ChatHistory.ChatHistoryItem(role=msg.role, message=msg.content) for msg in chat_session])

@router.post("/chat",response_model=AgentResponse)
async def chat_with_agent(request:AgentRequest,config: Settings = Depends(get_settings)) -> AgentResponse:
    """Endpoint to handle chat interactions with the sales agent."""

    orchestrator = SalesAgentOrchestrator(config=config.AGENT)
    response = await orchestrator.process_message(request.user_message,request.user_id, request.session_id,None,request.company_id)
    logger.info("Agent Response",session_id=request.session_id,response=response)
    return AgentResponse(session_id=request.session_id,message=response.message,needs_followup=response.needs_followup,followup_question=response.followup_question)


@router.get("/table_schema",response_model=dict)
async def get_table_schema(table_name:Annotated[list[str], Query(...)]):
    """Endpoint to retrieve the schema of specified database tables."""
    response={}
    for table in table_name:
        schema = table_schema_dict.get(table)
        if schema:
            response[table] = schema
        else:
            response[table] = "Schema not found"
    return response

@router.post("/{company_id}/execute_query",response_model=list[dict])
async def execute_query(company_id: str, query: ExecuteQueryRequest, db_pool: DatabasePoolDep,) -> list[dict]:
    """Endpoint to execute a SQL query and return the results."""
    async with db_pool.acquire() as connection:
        await set_search_path(connection,get_schema_name(company_id))
        results = await connection.fetch(query.sql_query)
        return [dict(record) for record in results]