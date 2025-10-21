"""
Wallet service utilities for managing user wallets and transactions
"""

from datetime import datetime
from flask import current_app
from models import db, Wallet, WalletTransaction, WithdrawalRequest, User, Earning

class WalletService:
    """Service class for wallet operations"""
    
    @staticmethod
    def get_or_create_wallet(user_id):
        """Get user's wallet or create one if it doesn't exist"""
        wallet = Wallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            wallet = Wallet(
                user_id=user_id,
                balance=0.0,
                currency='USD',
                is_active=True
            )
            db.session.add(wallet)
            db.session.commit()
        return wallet
    
    @staticmethod
    def add_earning_to_wallet(earning_id):
        """Add an earning to user's wallet balance"""
        earning = Earning.query.get(earning_id)
        if not earning or earning.status != 'paid':
            return False
        
        wallet = WalletService.get_or_create_wallet(earning.user_id)
        
        # Check if this earning was already processed
        existing_transaction = WalletTransaction.query.filter_by(
            reference_id=str(earning_id),
            reference_type='earning'
        ).first()
        
        if existing_transaction:
            return False
        
        # Create wallet transaction
        balance_before = wallet.balance
        wallet.balance += earning.amount
        balance_after = wallet.balance
        
        transaction = WalletTransaction(
            wallet_id=wallet.id,
            user_id=earning.user_id,
            transaction_type='deposit',
            amount=earning.amount,
            currency=earning.currency,
            balance_before=balance_before,
            balance_after=balance_after,
            description=f'Deposit from {earning.earning_type}: {earning.description}',
            reference_id=str(earning_id),
            reference_type='earning',
            status='completed',
            completed_at=datetime.utcnow()
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return True
    
    @staticmethod
    def create_transaction(wallet_id, user_id, transaction_type, amount, description, 
                          reference_id=None, reference_type=None, processing_fee=0.0):
        """Create a wallet transaction"""
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            return None
        
        # Calculate new balance
        if transaction_type in ['deposit', 'refund']:
            new_balance = wallet.balance + amount
        elif transaction_type in ['withdrawal', 'fee', 'transfer']:
            new_balance = wallet.balance - amount - processing_fee
            if new_balance < 0:
                return None  # Insufficient funds
        else:
            return None
        
        balance_before = wallet.balance
        wallet.balance = new_balance
        
        transaction = WalletTransaction(
            wallet_id=wallet_id,
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            currency=wallet.currency,
            balance_before=balance_before,
            balance_after=new_balance,
            description=description,
            reference_id=reference_id,
            reference_type=reference_type,
            processing_fee=processing_fee,
            status='completed' if transaction_type in ['deposit', 'refund'] else 'pending'
        )
        
        if transaction.status == 'completed':
            transaction.completed_at = datetime.utcnow()
        
        db.session.add(transaction)
        db.session.commit()
        
        return transaction
    
    @staticmethod
    def request_withdrawal(user_id, amount, payment_method, payment_details):
        """Create a withdrawal request"""
        wallet = WalletService.get_or_create_wallet(user_id)
        
        # Check minimum withdrawal amount (e.g., $10)
        if amount < 10.0:
            return None
        
        # Check maximum withdrawal amount (e.g., $10,000)
        if amount > 10000.0:
            return None
        
        if wallet.balance < amount:
            return None  # Insufficient funds
        
        withdrawal_request = WithdrawalRequest(
            user_id=user_id,
            wallet_id=wallet.id,
            amount=amount,
            currency=wallet.currency,
            requested_balance=wallet.balance,
            payment_method=payment_method,
            payment_details=payment_details,
            status='pending'
        )
        
        db.session.add(withdrawal_request)
        db.session.commit()
        
        return withdrawal_request
    
    @staticmethod
    def process_withdrawal(withdrawal_request_id, admin_id, approved=True, admin_notes=None):
        """Process a withdrawal request (approve/reject)"""
        withdrawal_request = WithdrawalRequest.query.get(withdrawal_request_id)
        if not withdrawal_request:
            return False
        
        if approved:
            # Create withdrawal transaction
            transaction = WalletService.create_transaction(
                wallet_id=withdrawal_request.wallet_id,
                user_id=withdrawal_request.user_id,
                transaction_type='withdrawal',
                amount=withdrawal_request.amount,
                description=f'Withdrawal via {withdrawal_request.payment_method}',
                reference_id=str(withdrawal_request_id),
                reference_type='withdrawal',
                processing_fee=withdrawal_request.processing_fee
            )
            
            if transaction:
                withdrawal_request.status = 'approved'
                withdrawal_request.processed_by_admin_id = admin_id
                withdrawal_request.processed_at = datetime.utcnow()
                withdrawal_request.admin_notes = admin_notes
                db.session.commit()
                return True
            else:
                return False  # Insufficient funds
        else:
            withdrawal_request.status = 'rejected'
            withdrawal_request.processed_by_admin_id = admin_id
            withdrawal_request.processed_at = datetime.utcnow()
            withdrawal_request.admin_notes = admin_notes
            db.session.commit()
            return True
    
    @staticmethod
    def get_wallet_summary(user_id):
        """Get comprehensive wallet summary for user"""
        wallet = WalletService.get_or_create_wallet(user_id)
        
        # Get recent transactions
        recent_transactions = WalletTransaction.query.filter_by(
            user_id=user_id
        ).order_by(WalletTransaction.created_at.desc()).limit(10).all()
        
        # Get pending withdrawal requests
        pending_withdrawals = WithdrawalRequest.query.filter_by(
            user_id=user_id,
            status='pending'
        ).all()
        
        # Get recent withdrawal requests (including rejected/completed ones)
        recent_withdrawals = WithdrawalRequest.query.filter_by(
            user_id=user_id
        ).order_by(WithdrawalRequest.created_at.desc()).limit(5).all()
        
        # Get total earnings
        total_earnings = db.session.query(db.func.sum(Earning.amount)).filter_by(
            user_id=user_id,
            status='paid'
        ).scalar() or 0
        
        # Get total withdrawals
        total_withdrawals = db.session.query(db.func.sum(WithdrawalRequest.amount)).filter_by(
            user_id=user_id,
            status='approved'
        ).scalar() or 0
        
        return {
            'wallet': wallet,
            'recent_transactions': recent_transactions,
            'pending_withdrawals': pending_withdrawals,
            'recent_withdrawals': recent_withdrawals,
            'total_earnings': total_earnings,
            'total_withdrawals': total_withdrawals,
            'available_balance': wallet.balance
        }
    
    @staticmethod
    def sync_earnings_to_wallet(user_id):
        """Sync all paid earnings to wallet (for existing users)"""
        paid_earnings = Earning.query.filter_by(
            user_id=user_id,
            status='paid'
        ).all()
        
        synced_count = 0
        for earning in paid_earnings:
            if WalletService.add_earning_to_wallet(earning.id):
                synced_count += 1
        
        return synced_count
