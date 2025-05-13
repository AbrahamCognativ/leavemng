#!/usr/bin/env python3
"""
Script to check the audit_logs table in the database.
This will print out the contents of the table to help debug issues.
"""

import sys
import os
import json

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from app.db.session import get_db
    from app.models.audit_log import AuditLog
    
    # Create a database session
    db = next(get_db())
    
    # Query all audit logs
    audit_logs = db.query(AuditLog).all()
    
    print(f"Found {len(audit_logs)} audit logs in the database.")
    
    # Print details of each log
    for i, log in enumerate(audit_logs):
        print(f"\nLog #{i+1}:")
        print(f"  ID: {log.id}")
        print(f"  User ID: {log.user_id}")
        print(f"  Action: {log.action}")
        print(f"  Resource Type: {log.resource_type}")
        print(f"  Resource ID: {log.resource_id}")
        print(f"  Timestamp: {log.timestamp}")
        if log.extra_metadata:
            print(f"  Metadata: {json.dumps(log.extra_metadata, indent=2)}")
    
    # If no logs found, let's manually insert a test log
    if len(audit_logs) == 0:
        print("\nNo audit logs found. Creating a test log...")
        
        # Get a user to associate with the log
        from app.models.user import User
        user = db.query(User).first()
        
        if user:
            from datetime import datetime, timezone
            import uuid
            
            # Create a test audit log
            test_log = AuditLog(
                id=uuid.uuid4(),
                user_id=user.id,
                action="test_action",
                resource_type="test_resource",
                resource_id=user.id,
                timestamp=datetime.now(timezone.utc),
                extra_metadata={"test": True, "created_by": "debug_script"}
            )
            
            db.add(test_log)
            db.commit()
            
            print(f"Created test audit log with ID: {test_log.id}")
        else:
            print("No users found in the database. Cannot create test log.")
    
except Exception as e:
    print(f"Error: {e}")
    
    # Check if the audit_logs table exists
    try:
        import psycopg2
        from app.settings import get_settings
        
        settings = get_settings()
        conn = psycopg2.connect(settings.DATABASE_URL)
        cursor = conn.cursor()
        
        # Check if the audit_logs table exists
        cursor.execute("""
            SELECT EXISTS (
               SELECT FROM information_schema.tables 
               WHERE table_name = 'audit_logs'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        print(f"Audit logs table exists: {table_exists}")
        
        if table_exists:
            # Check table structure
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'audit_logs';
            """)
            
            columns = cursor.fetchall()
            print("\nTable structure:")
            for col in columns:
                print(f"  {col[0]}: {col[1]}")
        
        conn.close()
        
    except Exception as db_error:
        print(f"Database connection error: {db_error}")
