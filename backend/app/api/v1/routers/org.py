from app.deps.permissions import get_current_user, require_role
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.schemas.org_unit import OrgUnitRead, OrgUnitCreate, OrgUnitTree
from app.models.org_unit import OrgUnit
from app.models.user import User
from app.db.session import get_db
from uuid import UUID
from typing import List
from typing import Dict, Any
import uuid
import json

router = APIRouter()


@router.get("/", tags=["org"], response_model=list[OrgUnitRead],
            dependencies=[Depends(require_role(["HR", "Admin"]))])
def list_org_units(db: Session = Depends(get_db)):
    units = db.query(OrgUnit).all()
    return [OrgUnitRead.model_validate(unit) for unit in units]


@router.get("/tree", tags=["org"], response_model=List[OrgUnitTree],
            dependencies=[Depends(require_role(["HR", "Admin"]))])
def get_org_tree(db: Session = Depends(get_db)):
    """
    Get the complete organization tree structure with managers for each unit.
    Returns a list of root-level org units with their complete hierarchy.
    """
    def get_unit_tree(unit: OrgUnit) -> OrgUnitTree:
        # Get all managers for this unit
        managers = db.query(User).filter(
            User.org_unit_id == unit.id,
            User.manager_id.is_(None)  # Only get top-level managers
        ).all()

        # Get all children recursively
        children = [get_unit_tree(child) for child in unit.children]

        return OrgUnitTree(
            id=unit.id,
            name=unit.name,
            parent_unit_id=unit.parent_unit_id,
            managers=[{
                "id": manager.id,
                "name": manager.name,
                "email": manager.email,
                "role_title": manager.role_title
            } for manager in managers],
            children=children
        )

    # Get all root-level org units (those without parents)
    root_units = db.query(OrgUnit).filter(
        OrgUnit.parent_unit_id.is_(None)).all()

    # Build the tree for each root unit
    return [get_unit_tree(unit) for unit in root_units]


@router.post("/", tags=["org"], response_model=OrgUnitRead,
             dependencies=[Depends(require_role(["HR", "Admin"]))])
def create_org_unit(
        unit: OrgUnitCreate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)):
    db_unit = OrgUnit(**unit.model_dump())
    db.add(db_unit)
    try:
        db.commit()
        db.refresh(db_unit)
    except Exception as e:
        db.rollback()
        orig = getattr(e, 'orig', None)
        if orig is not None and hasattr(orig, 'diag') and 'unique' in str(orig).lower():
            raise HTTPException(
                status_code=400,
                detail="Org unit with this name already exists")
        raise HTTPException(status_code=500, detail="Internal server error")
    from app.deps.permissions import log_permission_denied
    log_permission_denied(db, current_user.id, "create_org_unit", "org_unit", str(
        db_unit.id), message="Org unit creation failed or duplicate", http_status=400)
    return OrgUnitRead.model_validate(db_unit)


@router.get("/{unit_id}", tags=["org"], response_model=OrgUnitRead,
            dependencies=[Depends(require_role(["HR", "Admin"]))])
def get_org_unit(unit_id: UUID, db: Session = Depends(get_db)):
    unit = db.query(OrgUnit).filter(OrgUnit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Org unit not found")
    return OrgUnitRead.model_validate(unit)


@router.put("/{unit_id}", tags=["org"], response_model=OrgUnitRead,
            dependencies=[Depends(require_role(["HR", "Admin"]))])
def update_org_unit(
        unit_id: UUID,
        unit_update: OrgUnitCreate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)):
    unit = db.query(OrgUnit).filter(OrgUnit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Org unit not found")
    for k, v in unit_update.model_dump().items():
        setattr(unit, k, v)
    try:
        db.commit()
        db.refresh(unit)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not update org unit")
    from app.deps.permissions import log_permission_denied
    log_permission_denied(
        db,
        current_user.id,
        "update_org_unit",
        "org_unit",
        str(unit_id),
        message="Org unit update failed",
        http_status=500)
    return OrgUnitRead.model_validate(unit)


@router.get("/chart/tree", tags=["org"])
def get_org_chart(db: Session = Depends(get_db),
                  current_user=Depends(get_current_user)):
    """
    Get the organizational chart structure as a hierarchical tree.
    Returns a list of top-level org units with their children and users.
    """
    try:
        # Get all top-level org units (units without a parent)
        root_units = db.query(OrgUnit).filter(
            OrgUnit.parent_unit_id.is_(None)).all()

        if not root_units:
            # If no org units exist, create a default response structure
            print("No organization units found in database")
            return Response(
                content=json.dumps(
                    [],
                    default=str),
                media_type="application/json")

        result = []
        for unit in root_units:
            # Build a hierarchical representation of each org unit
            unit_dict = build_org_unit_dict(unit, db)
            result.append(unit_dict)

        # Log the first part of the result for debugging
        print(f"Generated org chart with {len(result)} root units")
        if result:
            print(
                f"First unit: {result[0]['name'] if 'name' in result[0] else 'Unknown'}")

        # Return as a plain JSON response to avoid Pydantic validation issues
        return Response(
            content=json.dumps(
                result,
                default=str),
            media_type="application/json")
    except Exception as e:
        import traceback
        print(f"Error in get_org_chart: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500,
                            detail="Failed to generate organization chart")


def generate_id():
    return str(uuid.uuid4())


def build_org_unit_dict(unit: OrgUnit, db: Session) -> Dict[str, Any]:
    """
    Build a dictionary representation of an org unit with its users and child units
    """
    try:

        # Basic unit info
        unit_dict = {
            "id": str(unit.id),
            "name": unit.name,
            "type": "unit",
            "children": []
        }

        # Group users by role title and role band
        users_by_role = {}

        # Check if the relationship is loaded
        if hasattr(unit, 'users'):
            # Handle possible SQLAlchemy lazy loading issues
            try:
                unit_users = list(unit.users)  # Force load the relationship
                print(
                    f"Found {len(unit_users)} users for org unit {unit.name}")
            except (AttributeError, TypeError, SQLAlchemyError) as e:
                print(
                    f"Error loading users for org unit {unit.name}: {str(e)}")
                unit_users = []

            for user in unit_users:
                try:
                    role_key = user.role_title if hasattr(
                        user, 'role_title') else 'Unknown Role'

                    if role_key not in users_by_role:
                        # Create a new role entry
                        role_band = user.role_band if hasattr(
                            user, 'role_band') else 'unknown'
                        role_id = f"role_{role_band}_{role_key.replace(' ', '_')}_{unit.id}"

                        users_by_role[role_key] = {
                            "id": role_id,
                            "title": role_key,
                            "type": "role",
                            "is_manager": "manager" in role_key.lower(),  # Simple check for manager roles
                            "users": [],
                            "children": []
                        }

                    # Add user to their role
                    user_name = user.name if hasattr(
                        user, 'name') else f"User {user.id}"
                    users_by_role[role_key]["users"].append({
                        "id": str(user.id),
                        "name": user_name
                    })
                except (AttributeError, TypeError, SQLAlchemyError) as user_err:
                    print(
                        f"Error processing user {getattr(user, 'id', 'unknown')}: {str(user_err)}")

            # Add manager-subordinate relationships
            for user in unit_users:
                try:
                    if hasattr(user, 'manager_id') and user.manager_id:
                        # Find the manager
                        manager = db.query(User).filter(
                            User.id == user.manager_id).first()
                        if manager and manager.org_unit_id == unit.id:
                            # If manager is in the same org unit, link their
                            # roles
                            manager_role_key = manager.role_title if hasattr(
                                manager, 'role_title') else 'Unknown Role'
                            user_role_key = user.role_title if hasattr(
                                user, 'role_title') else 'Unknown Role'

                            if manager_role_key in users_by_role and user_role_key in users_by_role:
                                # Add this role as a child of the manager's
                                # role if not already added
                                if not any(child["id"] == users_by_role[user_role_key]["id"]
                                           for child in users_by_role[manager_role_key]["children"]):
                                    users_by_role[manager_role_key]["children"].append(
                                        users_by_role[user_role_key])
                except (AttributeError, TypeError, SQLAlchemyError) as mgr_err:
                    print(
                        f"Error processing manager relationship for user {getattr(user, 'id', 'unknown')}: {str(mgr_err)}")
        else:
            print(
                f"Warning: 'users' relationship not loaded for org unit {unit.name}")

        # Add roles to the unit
        for role_dict in users_by_role.values():
            # Only add roles that aren't already child of another role
            if not any(role_dict["id"] == child["id"] for role in users_by_role.values(
            ) for child in role["children"]):
                unit_dict["children"].append(role_dict)

        # Add child units
        try:
            children = db.query(OrgUnit).filter(
                OrgUnit.parent_unit_id == unit.id).all()
            for child in children:
                child_dict = build_org_unit_dict(child, db)
                unit_dict["children"].append(child_dict)
        except (AttributeError, TypeError, SQLAlchemyError) as child_err:
            print(
                f"Error loading child units for {unit.name}: {str(child_err)}")

        return unit_dict
    except Exception as e:
        # Broad catch is used here to ensure a valid structure is always returned, even for unexpected errors.
        import traceback
        print(
            f"Error in build_org_unit_dict for unit {getattr(unit, 'name', 'unknown')}: {str(e)}")
        print(traceback.format_exc())
        return {
            "id": str(getattr(unit, 'id', 'unknown')),
            "name": getattr(unit, 'name', 'Error processing unit'),
            "type": "unit",
            "children": []
        }
