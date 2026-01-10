"""
Script to set user account to elite (unlimited) plan.
Run: python -m scripts.make_user_free
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.subscription import Subscription
from app.core.security import hash_password
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def make_user_elite(email: str, password: str = None):
    """Create or update user to elite plan with unlimited features."""
    db = SessionLocal()
    try:
        # Find or create user
        user = db.query(User).filter(User.email == email.lower()).first()
        
        if not user:
            if not password:
                logger.error(f"User {email} not found and no password provided. Cannot create user.")
                return False
            
            # Create new user
            logger.info(f"Creating new user: {email}")
            hashed_password = hash_password(password)
            user = User(
                email=email.lower(),
                full_name="Free User",
                password_hash=hashed_password,
                visa_status="Citizen"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Created user with ID: {user.id}")
        else:
            logger.info(f"Found existing user: {email} (ID: {user.id})")
        
        # Update or create subscription to elite (unlimited)
        # Use raw SQL to avoid schema issues
        try:
            subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
            
            if subscription:
                logger.info(f"Updating existing subscription to elite plan")
                subscription.plan_type = "elite"
                subscription.status = "active"
            else:
                logger.info(f"Creating new subscription for user {user.id} with elite plan")
                # Create subscription with minimal fields to avoid schema issues
                subscription = Subscription(
                    user_id=user.id,
                    plan_type="elite",
                    status="active"
                )
                db.add(subscription)
            
            db.commit()
            logger.info(f"Successfully set user {email} to elite plan (unlimited features)")
            return True
        except Exception as schema_error:
            logger.warning(f"Schema error with Subscription model, using raw SQL: {schema_error}")
            db.rollback()
            
            # Fallback: Use raw SQL to insert/update subscription
            from sqlalchemy import text
            try:
                # Try to update first
                result = db.execute(
                    text("UPDATE subscriptions SET plan_type = :plan, status = :status WHERE user_id = :user_id"),
                    {"plan": "elite", "status": "active", "user_id": user.id}
                )
                
                if result.rowcount == 0:
                    # Insert new subscription (only required fields)
                    db.execute(
                        text("INSERT INTO subscriptions (user_id, plan_type, status) VALUES (:user_id, :plan, :status)"),
                        {"user_id": user.id, "plan": "elite", "status": "active"}
                    )
                
                db.commit()
                logger.info(f"Successfully set user {email} to elite plan using raw SQL")
                return True
            except Exception as sql_error:
                db.rollback()
                logger.error(f"Raw SQL also failed: {sql_error}", exc_info=True)
                raise
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user: {e}", exc_info=True)
        return False
    finally:
        db.close()


if __name__ == "__main__":
    email = "lokauday456@gmail.com"
    password = "Bittu369@"
    
    logger.info(f"Setting up user: {email}")
    success = make_user_elite(email, password)
    
    if success:
        print(f"\n[SUCCESS] User {email} is now on elite plan with unlimited features!")
        print(f"   Password: {password}")
    else:
        print(f"\n[ERROR] Failed to setup user {email}")
        sys.exit(1)
