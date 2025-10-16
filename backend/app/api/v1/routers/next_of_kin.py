from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas.next_of_kin import NextOfKinContact, NextOfKinCreate, NextOfKinUpdate
from app.deps.permissions import get_current_user, UserInToken
from typing import List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=List[NextOfKinContact])
def get_next_of_kin(
    current_user: UserInToken = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's next of kin contacts"""
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        extra_metadata = user.extra_metadata or {}
        next_of_kin_data = extra_metadata.get('next_of_kin', [])
        
        # Convert dict to NextOfKinContact objects for validation
        contacts = []
        for contact_dict in next_of_kin_data:
            try:
                contact = NextOfKinContact(**contact_dict)
                contacts.append(contact)
            except Exception as e:
                logger.warning(f"Invalid next of kin contact data for user {user.id}: {e}")
                continue
        
        logger.info(f"Returning {len(contacts)} valid contacts for user {user.id}")
        return contacts
    except Exception as e:
        logger.error(f"Error getting next of kin for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("", response_model=NextOfKinContact)
def create_next_of_kin(
    contact: NextOfKinCreate,
    current_user: UserInToken = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new next of kin contact"""
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get existing next of kin data
        extra_metadata = user.extra_metadata or {}
        next_of_kin_data = extra_metadata.get('next_of_kin', [])
        
        logger.info(f"Creating next of kin for user {user.id}. Existing contacts: {len(next_of_kin_data)}")
        
        # If setting as primary, unset other primary contacts
        if contact.is_primary:
            for existing_contact in next_of_kin_data:
                existing_contact['is_primary'] = False
        
        # Create new contact with generated ID and timestamps
        new_contact = NextOfKinContact(
            relationship=contact.relationship,
            full_name=contact.full_name,
            phone_number=contact.phone_number,
            email=contact.email,
            address=contact.address,
            is_primary=contact.is_primary,
            is_emergency_contact=contact.is_emergency_contact
        )
        
        # Add new contact to list
        next_of_kin_data.append(new_contact.model_dump())
        
        # Validate only the primary contact constraint, not the entire list
        primary_contacts = [contact for contact in next_of_kin_data if contact.get('is_primary', False)]
        if len(primary_contacts) > 1:
            logger.error(f"Multiple primary contacts found: {len(primary_contacts)}")
            raise HTTPException(status_code=400, detail="Only one primary contact is allowed")
        
        # Update user's extra_metadata
        extra_metadata['next_of_kin'] = next_of_kin_data
        user.extra_metadata = extra_metadata
        
        # Mark the field as changed for SQLAlchemy
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(user, 'extra_metadata')
        
        logger.info(f"Saving next of kin data for user {user.id}. Total contacts: {len(next_of_kin_data)}")
        
        try:
            db.commit()
            db.refresh(user)
            logger.info(f"Successfully saved next of kin data for user {user.id}")
        except Exception as e:
            logger.error(f"Database error for user {user.id}: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to save contact to database")
        
        
        # Log the action
        from app.utils.audit import create_audit_log
        create_audit_log(
            db=db,
            user_id=str(current_user.id),
            action="create_next_of_kin",
            resource_type="next_of_kin",
            resource_id=new_contact.id,
            metadata={
                "contact_name": new_contact.full_name,
                "relationship": new_contact.relationship,
                "is_primary": new_contact.is_primary
            }
        )
        
        return new_contact
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating next of kin for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{contact_id}", response_model=NextOfKinContact)
def update_next_of_kin(
    contact_id: str,
    contact_update: NextOfKinUpdate,
    current_user: UserInToken = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a next of kin contact"""
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        extra_metadata = user.extra_metadata or {}
        next_of_kin_data = extra_metadata.get('next_of_kin', [])
        
        # Find and update contact
        contact_found = False
        updated_contact = None
        
        for i, existing_contact in enumerate(next_of_kin_data):
            if existing_contact.get('id') == contact_id:
                # If setting as primary, unset other primary contacts
                if contact_update.is_primary:
                    for j, other_contact in enumerate(next_of_kin_data):
                        if j != i:
                            other_contact['is_primary'] = False
                
                # Update contact with new data
                updated_data = existing_contact.copy()
                for field, value in contact_update.model_dump(exclude_unset=True).items():
                    if value is not None:
                        updated_data[field] = value
                
                # Update timestamps
                updated_data['updated_at'] = datetime.utcnow().isoformat()
                
                # Validate the updated contact
                updated_contact = NextOfKinContact(**updated_data)
                next_of_kin_data[i] = updated_contact.model_dump()
                contact_found = True
                break
        
        if not contact_found:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        # Validate only the primary contact constraint
        primary_contacts = [contact for contact in next_of_kin_data if contact.get('is_primary', False)]
        if len(primary_contacts) > 1:
            logger.error(f"Multiple primary contacts found: {len(primary_contacts)}")
            raise HTTPException(status_code=400, detail="Only one primary contact is allowed")
        
        logger.info(f"Update validation passed. Total contacts: {len(next_of_kin_data)}")
        
        # Update user's extra_metadata
        extra_metadata['next_of_kin'] = next_of_kin_data
        user.extra_metadata = extra_metadata
        
        # Mark the field as changed for SQLAlchemy
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(user, 'extra_metadata')
        
        try:
            db.commit()
            db.refresh(user)
            logger.info(f"Successfully updated contact {contact_id} for user {user.id}")
        except Exception as e:
            logger.error(f"Database error updating contact {contact_id} for user {user.id}: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to update contact in database")
        
        # Log the action
        from app.utils.audit import create_audit_log
        create_audit_log(
            db=db,
            user_id=str(current_user.id),
            action="update_next_of_kin",
            resource_type="next_of_kin",
            resource_id=contact_id,
            metadata={
                "contact_name": updated_contact.full_name,
                "updated_fields": list(contact_update.model_dump(exclude_unset=True).keys())
            }
        )
        
        return updated_contact
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating next of kin {contact_id} for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{contact_id}")
def delete_next_of_kin(
    contact_id: str,
    current_user: UserInToken = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a next of kin contact"""
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        extra_metadata = user.extra_metadata or {}
        next_of_kin_data = extra_metadata.get('next_of_kin', [])
        
        logger.info(f"Deleting contact {contact_id} for user {user.id}")
        
        # Find contact to get name for logging
        contact_to_delete = None
        for contact in next_of_kin_data:
            if contact.get('id') == contact_id:
                contact_to_delete = contact
                break
        
        if not contact_to_delete:
            logger.error(f"Contact {contact_id} not found in user {user.id} data")
            raise HTTPException(status_code=404, detail="Contact not found")
        
        # Remove contact
        next_of_kin_data = [contact for contact in next_of_kin_data if contact.get('id') != contact_id]
        
        # Update user's extra_metadata
        extra_metadata['next_of_kin'] = next_of_kin_data
        user.extra_metadata = extra_metadata
        
        # Mark the field as changed for SQLAlchemy
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(user, 'extra_metadata')
        
        logger.info(f"Saving updated next of kin data for user {user.id}")
        
        try:
            db.commit()
            db.refresh(user)
            logger.info(f"Successfully deleted contact {contact_id} for user {user.id}")
        except Exception as e:
            logger.error(f"Database error deleting contact {contact_id} for user {user.id}: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to delete contact from database")
        
        # Log the action
        from app.utils.audit import create_audit_log
        create_audit_log(
            db=db,
            user_id=str(current_user.id),
            action="delete_next_of_kin",
            resource_type="next_of_kin",
            resource_id=contact_id,
            metadata={
                "contact_name": contact_to_delete.get('full_name', 'Unknown')
            }
        )
        
        return {"message": "Contact deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting next of kin {contact_id} for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/user/{user_id}", response_model=List[NextOfKinContact])
def get_user_next_of_kin(
    user_id: str,
    current_user: UserInToken = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get another user's next of kin contacts (Admin/HR/Manager only)"""
    try:
        # Check if current user has permission to view other users' next of kin
        if current_user.role_band not in ("HR", "Admin") and current_user.role_title not in ("HR", "Admin"):
            # Check if the user is a manager viewing their direct report
            target_user = db.query(User).filter(User.id == user_id).first()
            if not target_user or str(target_user.manager_id) != str(current_user.id):
                raise HTTPException(
                    status_code=403, 
                    detail="Insufficient permissions to view user's next of kin contacts"
                )
        
        # Get the target user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        extra_metadata = user.extra_metadata or {}
        next_of_kin_data = extra_metadata.get('next_of_kin', [])
        
        # Convert dict to NextOfKinContact objects for validation
        contacts = []
        for contact_dict in next_of_kin_data:
            try:
                contact = NextOfKinContact(**contact_dict)
                contacts.append(contact)
            except Exception as e:
                logger.warning(f"Invalid next of kin contact data for user {user.id}: {e}")
                continue
        
        # Log the action
        from app.utils.audit import create_audit_log
        create_audit_log(
            db=db,
            user_id=str(current_user.id),
            action="view_user_next_of_kin",
            resource_type="next_of_kin",
            resource_id=user_id,
            metadata={
                "target_user_name": user.name,
                "target_user_email": user.email,
                "contacts_count": len(contacts)
            }
        )
        
        return contacts
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting next of kin for user {user_id} by {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
