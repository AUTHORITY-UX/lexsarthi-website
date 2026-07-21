# =============================================================================
# payment_gateway.py – Razorpay Payment Integration
# =============================================================================

import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

import razorpay

logger = logging.getLogger("unknown_verdict.payment")

class PaymentGateway:
    """
    Razorpay payment gateway integration for Unknown Verdict.
    Handles order creation, verification, and subscription management.
    """
    
    def __init__(self):
        self.key_id = os.getenv("RAZORPAY_KEY_ID")
        self.key_secret = os.getenv("RAZORPAY_KEY_SECRET")
        self.client = None
        
        if self.key_id and self.key_secret:
            try:
                self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
                logger.info("✅ Razorpay client initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Razorpay: {e}")
        else:
            logger.warning("⚠️ Razorpay credentials not set – payment gateway disabled")
    
    def is_configured(self) -> bool:
        """Check if payment gateway is configured."""
        return self.client is not None
    
    def create_order(self, amount: int, currency: str = "INR", 
                    receipt: str = None, notes: Dict = None) -> Dict:
        """
        Create a Razorpay order.
        
        Args:
            amount: Amount in paise (e.g., 10000 = ₹100)
            currency: Currency code (default: INR)
            receipt: Optional receipt ID
            notes: Optional notes dict
        
        Returns:
            Dict with order details
        """
        if not self.is_configured():
            return {
                "status": "error",
                "error": "Payment gateway not configured"
            }
        
        try:
            order_data = {
                "amount": amount,
                "currency": currency,
                "payment_capture": 1
            }
            if receipt:
                order_data["receipt"] = receipt
            if notes:
                order_data["notes"] = notes
            
            order = self.client.order.create(order_data)
            logger.info(f"✅ Order created: {order['id']} for ₹{amount/100}")
            
            return {
                "status": "success",
                "order_id": order["id"],
                "amount": order["amount"],
                "currency": order["currency"],
                "receipt": order.get("receipt"),
                "razorpay_key": self.key_id
            }
            
        except Exception as e:
            error_msg = f"Failed to create order: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "error": error_msg}
    
    def verify_signature(self, order_id: str, payment_id: str, signature: str) -> Dict:
        """
        Verify Razorpay payment signature.
        
        Args:
            order_id: Razorpay order ID
            payment_id: Razorpay payment ID
            signature: Razorpay signature
        
        Returns:
            Dict with verification status
        """
        if not self.is_configured():
            return {
                "status": "error",
                "error": "Payment gateway not configured"
            }
        
        try:
            params = {
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature
            }
            
            self.client.utility.verify_payment_signature(params)
            logger.info(f"✅ Payment verified: {payment_id}")
            
            return {
                "status": "success",
                "order_id": order_id,
                "payment_id": payment_id,
                "verified": True
            }
            
        except Exception as e:
            error_msg = f"Signature verification failed: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg,
                "verified": False
            }
    
    def get_payment_details(self, payment_id: str) -> Dict:
        """Get payment details from Razorpay."""
        if not self.is_configured():
            return {"status": "error", "error": "Payment gateway not configured"}
        
        try:
            payment = self.client.payment.fetch(payment_id)
            return {
                "status": "success",
                "payment_id": payment["id"],
                "amount": payment["amount"],
                "currency": payment["currency"],
                "status": payment["status"],
                "method": payment["method"],
                "order_id": payment["order_id"],
                "created_at": datetime.fromtimestamp(payment["created_at"])
            }
        except Exception as e:
            logger.error(f"Failed to fetch payment: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_subscription_plans(self) -> Dict:
        """Get available subscription plans."""
        return {
            "plans": [
                {
                    "id": "free",
                    "name": "Free",
                    "price": 0,
                    "currency": "INR",
                    "interval": "month",
                    "features": ["10 queries/day", "Basic agents", "Community support"]
                },
                {
                    "id": "premium",
                    "name": "Premium",
                    "price": 1999,
                    "currency": "INR",
                    "interval": "month",
                    "features": ["Unlimited queries", "All 250 agents", "Priority support", "API access"]
                },
                {
                    "id": "enterprise",
                    "name": "Enterprise",
                    "price": 9999,
                    "currency": "INR",
                    "interval": "month",
                    "features": ["Everything in Premium", "Custom agents", "On-premise deployment", "Dedicated support", "SLA"]
                },
                {
                    "id": "lifetime",
                    "name": "Lifetime",
                    "price": 99999,
                    "currency": "INR",
                    "interval": "one-time",
                    "features": ["Everything in Enterprise", "One-time payment", "Lifetime updates", "Priority feature requests"]
                }
            ]
        }