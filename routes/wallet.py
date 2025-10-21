"""
Wallet routes for user financial management
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from utils.permissions import require_permission
from utils.wallet_service import WalletService
from models import db, Wallet, WalletTransaction, WithdrawalRequest, Earning

wallet_bp = Blueprint('wallet', __name__, url_prefix='/wallet')

@wallet_bp.route('/')
@login_required
@require_permission('wallet', 'view')
def index():
    """Wallet dashboard"""
    try:
        # Get wallet summary
        summary = WalletService.get_wallet_summary(current_user.id)
        
        # Get earnings statistics
        earnings_stats = {
            'total_earned': db.session.query(db.func.sum(Earning.amount)).filter_by(
                user_id=current_user.id,
                status='paid'
            ).scalar() or 0,
            'pending_earnings': db.session.query(db.func.sum(Earning.amount)).filter_by(
                user_id=current_user.id,
                status='pending'
            ).scalar() or 0,
            'this_month': db.session.query(db.func.sum(Earning.amount)).filter(
                Earning.user_id == current_user.id,
                Earning.status == 'paid',
                Earning.paid_at >= datetime.utcnow().replace(day=1)
            ).scalar() or 0,
            'last_month': db.session.query(db.func.sum(Earning.amount)).filter(
                Earning.user_id == current_user.id,
                Earning.status == 'paid',
                Earning.paid_at >= (datetime.utcnow().replace(day=1) - timedelta(days=1)).replace(day=1),
                Earning.paid_at < datetime.utcnow().replace(day=1)
            ).scalar() or 0
        }
        
        return render_template('wallet/index.html', 
                             summary=summary, 
                             earnings_stats=earnings_stats)
    except Exception as e:
        flash('Error loading wallet dashboard', 'error')
        return redirect(url_for('dashboard.index'))

@wallet_bp.route('/transactions')
@login_required
@require_permission('wallet', 'view_transactions')
def transactions():
    """Transaction history"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        transactions = WalletTransaction.query.filter_by(
            user_id=current_user.id
        ).order_by(WalletTransaction.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('wallet/transactions.html', transactions=transactions)
    except Exception as e:
        flash('Error loading transaction history', 'error')
        return redirect(url_for('wallet.index'))

@wallet_bp.route('/withdraw')
@login_required
@require_permission('wallet', 'withdraw')
def withdraw():
    """Withdrawal form"""
    try:
        wallet = WalletService.get_or_create_wallet(current_user.id)
        
        # Get pending withdrawal requests
        pending_withdrawals = WithdrawalRequest.query.filter_by(
            user_id=current_user.id,
            status='pending'
        ).order_by(WithdrawalRequest.created_at.desc()).all()
        
        return render_template('wallet/withdraw.html', 
                             wallet=wallet, 
                             pending_withdrawals=pending_withdrawals)
    except Exception as e:
        flash('Error loading withdrawal page', 'error')
        return redirect(url_for('wallet.index'))

@wallet_bp.route('/withdraw', methods=['POST'])
@login_required
@require_permission('withdrawals', 'request')
def submit_withdrawal():
    """Submit withdrawal request"""
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))
        payment_method = data.get('payment_method')
        payment_details = data.get('payment_details', {})
        
        if amount < 10:
            return jsonify({'success': False, 'message': 'Minimum withdrawal amount is $10'})
        
        if amount > 10000:
            return jsonify({'success': False, 'message': 'Maximum withdrawal amount is $10,000'})
        
        # Check wallet balance
        wallet = WalletService.get_or_create_wallet(current_user.id)
        if amount > wallet.balance:
            return jsonify({'success': False, 'message': f'Insufficient funds. Available balance: ${wallet.balance:.2f}'})
        
        # Validate payment details based on method
        if payment_method == 'bank_transfer':
            required_fields = ['account_number', 'routing_number', 'account_holder_name']
            if not all(payment_details.get(field) for field in required_fields):
                return jsonify({'success': False, 'message': 'Missing required bank transfer details'})
        elif payment_method == 'paypal':
            if not payment_details.get('email'):
                return jsonify({'success': False, 'message': 'PayPal email is required'})
        elif payment_method == 'stripe':
            if not payment_details.get('stripe_account_id'):
                return jsonify({'success': False, 'message': 'Stripe account ID is required'})
        
        withdrawal_request = WalletService.request_withdrawal(
            current_user.id, amount, payment_method, payment_details
        )
        
        if withdrawal_request:
            return jsonify({
                'success': True, 
                'message': 'Withdrawal request submitted successfully',
                'request_id': withdrawal_request.id
            })
        else:
            return jsonify({'success': False, 'message': 'Insufficient funds or invalid request'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error processing withdrawal request'})

@wallet_bp.route('/earnings')
@login_required
@require_permission('earnings', 'view')
def earnings():
    """Earnings history"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        earnings = Earning.query.filter_by(
            user_id=current_user.id
        ).order_by(Earning.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('wallet/earnings.html', earnings=earnings)
    except Exception as e:
        flash('Error loading earnings history', 'error')
        return redirect(url_for('wallet.index'))

@wallet_bp.route('/sync-earnings', methods=['POST'])
@login_required
@require_permission('earnings', 'sync')
def sync_earnings():
    """Sync paid earnings to wallet"""
    try:
        synced_count = WalletService.sync_earnings_to_wallet(current_user.id)
        
        if synced_count > 0:
            return jsonify({
                'success': True, 
                'message': f'Synced {synced_count} earnings to wallet'
            })
        else:
            return jsonify({
                'success': True, 
                'message': 'No new earnings to sync'
            })
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error syncing earnings'})

@wallet_bp.route('/api/balance')
@login_required
def api_balance():
    """API endpoint to get current wallet balance"""
    try:
        wallet = WalletService.get_or_create_wallet(current_user.id)
        return jsonify({
            'balance': wallet.balance,
            'currency': wallet.currency
        })
    except Exception as e:
        return jsonify({'error': 'Error fetching balance'}), 500

