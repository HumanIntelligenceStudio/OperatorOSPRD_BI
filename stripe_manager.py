"""
Stripe Payment Manager for OperatorOS
Handles payment link creation, invoice generation, and webhook processing
"""
import os
import stripe
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from models import db, Payment, PaymentStatus
from notifications import NotificationManager

# Initialize Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

class StripeManager:
    """Manager for Stripe payment operations"""
    
    def __init__(self):
        self.notification_manager = NotificationManager()
        
    def create_payment_link(self, project_name: str, client_name: str, 
                           client_email: str, amount: float, description: str = None) -> Dict[str, Any]:
        """Create a Stripe payment link"""
        try:
            # Create a payment link in Stripe
            payment_link = stripe.PaymentLink.create(
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'{project_name} - {client_name}',
                            'description': description or f'Payment for project: {project_name}'
                        },
                        'unit_amount': int(amount * 100),  # Convert to cents
                    },
                    'quantity': 1,
                }],
                metadata={
                    'project_name': project_name,
                    'client_name': client_name,
                    'client_email': client_email
                }
            )
            
            # Save payment record to database
            payment = Payment(
                stripe_payment_id=payment_link.id,
                project_name=project_name,
                client_name=client_name,
                client_email=client_email,
                amount=amount,
                description=description,
                payment_type='link',
                status=PaymentStatus.PENDING,
                payment_url=payment_link.url
            )
            
            db.session.add(payment)
            db.session.commit()
            
            # Send notification
            self.notification_manager.add_notification(
                "Payment Link Created",
                f"Payment link created for {client_name} - ${amount:.2f}",
                "info",
                {"payment_id": payment.id, "client_email": client_email}
            )
            
            logging.info(f"Payment link created for {client_name}: {payment_link.url}")
            
            return {
                "success": True,
                "payment_id": payment.id,
                "stripe_id": payment_link.id,
                "payment_url": payment_link.url,
                "message": f"Payment link created successfully for ${amount:.2f}"
            }
            
        except stripe.error.StripeError as e:
            logging.error(f"Stripe error creating payment link: {str(e)}")
            return {
                "success": False,
                "error": f"Stripe error: {str(e)}"
            }
        except Exception as e:
            logging.error(f"Error creating payment link: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to create payment link: {str(e)}"
            }
    
    def create_invoice(self, project_name: str, client_name: str, 
                      client_email: str, amount: float, description: str = None,
                      due_days: int = 30) -> Dict[str, Any]:
        """Create and send a Stripe invoice"""
        try:
            # Create or retrieve customer
            customers = stripe.Customer.list(email=client_email, limit=1)
            if customers.data:
                customer = customers.data[0]
            else:
                customer = stripe.Customer.create(
                    email=client_email,
                    name=client_name,
                    metadata={
                        'source': 'OperatorOS'
                    }
                )
            
            # Create invoice item
            stripe.InvoiceItem.create(
                customer=customer.id,
                amount=int(amount * 100),  # Convert to cents
                currency='usd',
                description=description or f'Payment for project: {project_name}',
                metadata={
                    'project_name': project_name,
                    'client_name': client_name
                }
            )
            
            # Create invoice
            invoice = stripe.Invoice.create(
                customer=customer.id,
                collection_method='send_invoice',
                days_until_due=due_days,
                metadata={
                    'project_name': project_name,
                    'client_name': client_name,
                    'client_email': client_email
                }
            )
            
            # Finalize and send invoice
            stripe.Invoice.finalize_invoice(invoice.id)
            stripe.Invoice.send_invoice(invoice.id)
            
            # Calculate due date
            due_date = datetime.utcnow() + timedelta(days=due_days)
            
            # Save payment record to database
            payment = Payment(
                stripe_invoice_id=invoice.id,
                project_name=project_name,
                client_name=client_name,
                client_email=client_email,
                amount=amount,
                description=description,
                payment_type='invoice',
                status=PaymentStatus.PENDING,
                payment_url=invoice.hosted_invoice_url,
                due_date=due_date
            )
            
            db.session.add(payment)
            db.session.commit()
            
            # Send notification
            self.notification_manager.add_notification(
                "Invoice Created & Sent",
                f"Invoice sent to {client_name} ({client_email}) - ${amount:.2f}",
                "info",
                {"payment_id": payment.id, "invoice_id": invoice.id}
            )
            
            logging.info(f"Invoice created and sent to {client_email}: {invoice.hosted_invoice_url}")
            
            return {
                "success": True,
                "payment_id": payment.id,
                "stripe_id": invoice.id,
                "invoice_url": invoice.hosted_invoice_url,
                "due_date": due_date.isoformat(),
                "message": f"Invoice created and sent to {client_email} for ${amount:.2f}"
            }
            
        except stripe.error.StripeError as e:
            logging.error(f"Stripe error creating invoice: {str(e)}")
            return {
                "success": False,
                "error": f"Stripe error: {str(e)}"
            }
        except Exception as e:
            logging.error(f"Error creating invoice: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to create invoice: {str(e)}"
            }
    
    def handle_webhook(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """Handle Stripe webhook events"""
        try:
            # Verify webhook signature
            webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
            if webhook_secret:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, webhook_secret
                )
            else:
                # For development - parse without verification
                event = stripe.Event.construct_from(
                    stripe.util.json.loads(payload), stripe.api_key
                )
            
            logging.info(f"Received Stripe webhook: {event['type']}")
            
            # Handle payment success events
            if event['type'] == 'payment_intent.succeeded':
                return self._handle_payment_success(event['data']['object'])
            elif event['type'] == 'invoice.payment_succeeded':
                return self._handle_invoice_payment_success(event['data']['object'])
            elif event['type'] == 'payment_intent.payment_failed':
                return self._handle_payment_failed(event['data']['object'])
            elif event['type'] == 'invoice.payment_failed':
                return self._handle_invoice_payment_failed(event['data']['object'])
            
            return {"success": True, "message": f"Webhook {event['type']} processed"}
            
        except stripe.error.SignatureVerificationError as e:
            logging.error(f"Webhook signature verification failed: {str(e)}")
            return {"success": False, "error": "Invalid signature"}
        except Exception as e:
            logging.error(f"Error processing webhook: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _handle_payment_success(self, payment_intent) -> Dict[str, Any]:
        """Handle successful payment intent"""
        try:
            # Find payment by Stripe ID in metadata or description
            payment = Payment.query.filter(
                Payment.stripe_payment_id.like(f"%{payment_intent.id}%")
            ).first()
            
            if payment:
                payment.status = PaymentStatus.PAID
                payment.paid_at = datetime.utcnow()
                db.session.commit()
                
                # Send notification
                self.notification_manager.add_notification(
                    "Payment Received",
                    f"Payment received from {payment.client_name} - ${payment.amount:.2f}",
                    "success",
                    {"payment_id": payment.id, "amount": payment.amount}
                )
                
                logging.info(f"Payment marked as paid: {payment.id}")
            
            return {"success": True, "message": "Payment success processed"}
            
        except Exception as e:
            logging.error(f"Error handling payment success: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _handle_invoice_payment_success(self, invoice) -> Dict[str, Any]:
        """Handle successful invoice payment"""
        try:
            # Find payment by Stripe invoice ID
            payment = Payment.query.filter_by(stripe_invoice_id=invoice.id).first()
            
            if payment:
                payment.status = PaymentStatus.PAID
                payment.paid_at = datetime.utcnow()
                db.session.commit()
                
                # Send notification
                self.notification_manager.add_notification(
                    "Invoice Payment Received",
                    f"Invoice payment received from {payment.client_name} - ${payment.amount:.2f}",
                    "success",
                    {"payment_id": payment.id, "invoice_id": invoice.id}
                )
                
                logging.info(f"Invoice payment marked as paid: {payment.id}")
            
            return {"success": True, "message": "Invoice payment success processed"}
            
        except Exception as e:
            logging.error(f"Error handling invoice payment success: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _handle_payment_failed(self, payment_intent) -> Dict[str, Any]:
        """Handle failed payment"""
        try:
            # Find payment by Stripe ID
            payment = Payment.query.filter(
                Payment.stripe_payment_id.like(f"%{payment_intent.id}%")
            ).first()
            
            if payment:
                payment.status = PaymentStatus.FAILED
                db.session.commit()
                
                # Send notification
                self.notification_manager.add_notification(
                    "Payment Failed",
                    f"Payment failed for {payment.client_name} - ${payment.amount:.2f}",
                    "error",
                    {"payment_id": payment.id, "reason": payment_intent.last_payment_error}
                )
                
                logging.warning(f"Payment marked as failed: {payment.id}")
            
            return {"success": True, "message": "Payment failure processed"}
            
        except Exception as e:
            logging.error(f"Error handling payment failure: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _handle_invoice_payment_failed(self, invoice) -> Dict[str, Any]:
        """Handle failed invoice payment"""
        try:
            # Find payment by Stripe invoice ID
            payment = Payment.query.filter_by(stripe_invoice_id=invoice.id).first()
            
            if payment:
                payment.status = PaymentStatus.FAILED
                db.session.commit()
                
                # Send notification
                self.notification_manager.add_notification(
                    "Invoice Payment Failed",
                    f"Invoice payment failed for {payment.client_name} - ${payment.amount:.2f}",
                    "error",
                    {"payment_id": payment.id, "invoice_id": invoice.id}
                )
                
                logging.warning(f"Invoice payment marked as failed: {payment.id}")
            
            return {"success": True, "message": "Invoice payment failure processed"}
            
        except Exception as e:
            logging.error(f"Error handling invoice payment failure: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_payment_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get payment statistics for the last N days"""
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import func
            
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get payment counts by status
            status_counts = db.session.query(
                Payment.status,
                func.count(Payment.id).label('count'),
                func.sum(Payment.amount).label('total_amount')
            ).filter(
                Payment.created_at >= start_date
            ).group_by(Payment.status).all()
            
            stats = {
                'total_payments': 0,
                'total_amount': 0.0,
                'pending_count': 0,
                'paid_count': 0,
                'failed_count': 0,
                'pending_amount': 0.0,
                'paid_amount': 0.0,
                'failed_amount': 0.0
            }
            
            for status, count, amount in status_counts:
                stats['total_payments'] += count
                stats['total_amount'] += amount or 0.0
                stats[f'{status}_count'] = count
                stats[f'{status}_amount'] = amount or 0.0
            
            return stats
            
        except Exception as e:
            logging.error(f"Error getting payment stats: {str(e)}")
            return {}
    
    def test_stripe_connection(self) -> Dict[str, Any]:
        """Test Stripe API connection"""
        try:
            # Try to retrieve account information
            account = stripe.Account.retrieve()
            
            return {
                "success": True,
                "account_id": account.id,
                "country": account.country,
                "currency": account.default_currency,
                "message": "Stripe connection successful"
            }
            
        except stripe.error.AuthenticationError:
            return {
                "success": False,
                "error": "Invalid Stripe API key"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Stripe connection failed: {str(e)}"
            }