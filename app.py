from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from models import db, MFAAccount
import pyotp
import os
from config import get_secret_key, get_database_path

app = Flask(__name__)
app.config['SECRET_KEY'] = get_secret_key()
# Use environment variable for database path in Docker, fallback to current directory
database_path = get_database_path()
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

@app.route('/')
def index():
    """Main dashboard showing all MFA accounts and their current codes"""
    # Check if user wants to show all accounts (including hidden)
    show_all = request.args.get('show_all', 'false').lower() == 'true'
    
    if show_all:
        accounts = MFAAccount.query.all()
    else:
        accounts = MFAAccount.query.filter_by(hidden=False).all()
    
    account_data = []
    
    for account in accounts:
        account_data.append({
            'id': account.id,
            'account_name': account.account_name,
            'issuer': account.issuer,
            'hidden': account.hidden,
            'totp_code': account.get_totp_code(),
            'remaining_time': account.get_remaining_time()
        })
    
    return render_template('index.html', accounts=account_data, show_all=show_all, theme=session.get('theme', 'light'))

@app.route('/add', methods=['GET', 'POST'])
def add_account():
    """Add a new MFA account"""
    if request.method == 'POST':
        account_name = request.form.get('account_name')
        secret = request.form.get('secret')
        issuer = request.form.get('issuer', 'MFA Manager')
        
        if not account_name or not secret:
            flash('Account name and secret are required!', 'error')
            return render_template('add_account.html', theme=session.get('theme', 'light'))
        
        # Validate secret format
        try:
            # Try to create a TOTP object to validate the secret
            pyotp.TOTP(secret).now()
        except Exception as e:
            flash(f'Invalid secret format: {str(e)}', 'error')
            return render_template('add_account.html', theme=session.get('theme', 'light'))
        
        # Check if account name already exists
        existing = MFAAccount.query.filter_by(account_name=account_name).first()
        if existing:
            flash('Account name already exists!', 'error')
            return render_template('add_account.html', theme=session.get('theme', 'light'))
        
        # Create new account
        new_account = MFAAccount(
            account_name=account_name,
            secret=secret.upper().replace(' ', ''),  # Normalize secret
            issuer=issuer
        )
        
        try:
            db.session.add(new_account)
            db.session.commit()
            flash(f'Account "{account_name}" added successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding account: {str(e)}', 'error')
    
    return render_template('add_account.html', theme=session.get('theme', 'light'))

@app.route('/generate_secret')
def generate_secret():
    """Generate a random secret for testing purposes"""
    secret = pyotp.random_base32()
    return jsonify({'secret': secret})

@app.route('/account/<int:account_id>')
def view_account(account_id):
    """View details for a specific account including QR code"""
    account = MFAAccount.query.get_or_404(account_id)
    
    account_data = {
        'id': account.id,
        'account_name': account.account_name,
        'issuer': account.issuer,
        'secret': account.secret,
        'hidden': account.hidden,
        'totp_code': account.get_totp_code(),
        'remaining_time': account.get_remaining_time(),
        'qr_code_image': account.generate_qr_code_image(),
        'qr_code_url': account.get_qr_code_url()
    }
    
    return render_template('account_detail.html', account=account_data, theme=session.get('theme', 'light'))

@app.route('/toggle_hidden/<int:account_id>', methods=['POST'])
def toggle_hidden(account_id):
    """Toggle the hidden status of an MFA account"""
    account = MFAAccount.query.get_or_404(account_id)
    account.hidden = not account.hidden
    status = 'hidden' if account.hidden else 'shown'
    
    try:
        db.session.commit()
        flash(f'Account "{account.account_name}" is now {status}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating account: {str(e)}', 'error')
    
    # Redirect back to the page they came from, preserving show_all parameter
    show_all = request.form.get('show_all', 'false').lower() == 'true'
    if show_all:
        return redirect(url_for('index', show_all='true'))
    return redirect(url_for('index'))

@app.route('/delete/<int:account_id>', methods=['POST'])
def delete_account(account_id):
    """Delete an MFA account"""
    account = MFAAccount.query.get_or_404(account_id)
    account_name = account.account_name
    
    try:
        db.session.delete(account)
        db.session.commit()
        flash(f'Account "{account_name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting account: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/edit/<int:account_id>', methods=['GET', 'POST'])
def edit_account(account_id):
    """Edit an existing MFA account"""
    account = MFAAccount.query.get_or_404(account_id)
    
    if request.method == 'POST':
        new_account_name = request.form.get('account_name')
        new_secret = request.form.get('secret')
        new_issuer = request.form.get('issuer', 'MFA Manager')
        
        if not new_account_name or not new_secret:
            flash('Account name and secret are required!', 'error')
            return render_template('edit_account.html', account=account, theme=session.get('theme', 'light'))
        
        # Validate secret format
        try:
            pyotp.TOTP(new_secret).now()
        except Exception as e:
            flash(f'Invalid secret format: {str(e)}', 'error')
            return render_template('edit_account.html', account=account, theme=session.get('theme', 'light'))
        
        # Check if new account name conflicts with existing (excluding current)
        if new_account_name != account.account_name:
            existing = MFAAccount.query.filter_by(account_name=new_account_name).first()
            if existing:
                flash('Account name already exists!', 'error')
                return render_template('edit_account.html', account=account, theme=session.get('theme', 'light'))
        
        # Get hidden status (checkbox returns 'on' if checked, otherwise not present)
        hidden = request.form.get('hidden') == 'on'
        
        # Update account
        account.account_name = new_account_name
        account.secret = new_secret.upper().replace(' ', '')
        account.issuer = new_issuer
        account.hidden = hidden
        
        try:
            db.session.commit()
            flash(f'Account "{new_account_name}" updated successfully!', 'success')
            return redirect(url_for('view_account', account_id=account.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating account: {str(e)}', 'error')
    
    return render_template('edit_account.html', account=account, theme=session.get('theme', 'light'))

@app.route('/api/codes')
def get_all_codes():
    """API endpoint to get all current TOTP codes (for auto-refresh)"""
    # Check if user wants to show all accounts (including hidden)
    show_all = request.args.get('show_all', 'false').lower() == 'true'
    
    if show_all:
        accounts = MFAAccount.query.all()
    else:
        accounts = MFAAccount.query.filter_by(hidden=False).all()
    
    codes = []
    
    for account in accounts:
        codes.append({
            'id': account.id,
            'account_name': account.account_name,
            'totp_code': account.get_totp_code(),
            'remaining_time': account.get_remaining_time()
        })
    
    return jsonify(codes)

@app.route('/api/code/<int:account_id>')
def get_single_code(account_id):
    """API endpoint to get TOTP code for a specific account"""
    account = MFAAccount.query.get_or_404(account_id)
    
    return jsonify({
        'id': account.id,
        'account_name': account.account_name,
        'totp_code': account.get_totp_code(),
        'remaining_time': account.get_remaining_time()
    })

@app.route('/api/search')
def search_accounts():
    """API endpoint to search for accounts by name or issuer"""
    query = request.args.get('q', '').strip()
    
    if not query:
        # Return all accounts if no query provided
        accounts = MFAAccount.query.all()
    else:
        # Search for accounts matching the query in account_name or issuer
        accounts = MFAAccount.query.filter(
            db.or_(
                MFAAccount.account_name.ilike(f'%{query}%'),
                MFAAccount.issuer.ilike(f'%{query}%')
            )
        ).all()
    
    results = []
    for account in accounts:
        results.append({
            'id': account.id,
            'account_name': account.account_name,
            'issuer': account.issuer,
            'totp_code': account.get_totp_code(),
            'remaining_time': account.get_remaining_time()
        })
    
    return jsonify(results)

@app.route('/api/theme', methods=['POST'])
def set_theme():
    """API endpoint to set user theme preference"""
    data = request.get_json()
    theme = data.get('theme', 'light')
    
    if theme in ['light', 'dark']:
        session['theme'] = theme
        return jsonify({'status': 'success', 'theme': theme})
    else:
        return jsonify({'status': 'error', 'message': 'Invalid theme'}), 400

@app.route('/api/theme', methods=['GET'])
def get_theme():
    """API endpoint to get user theme preference"""
    return jsonify({'theme': session.get('theme', 'light')})

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html', theme=session.get('theme', 'light')), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html', theme=session.get('theme', 'light')), 500

if __name__ == '__main__':
    from config import get_port, get_host, is_production
    
    with app.app_context():
        db.create_all()
        # Run migration to add hidden column if it doesn't exist
        try:
            from migrate_add_hidden_column import migrate
            migrate()
        except Exception as e:
            # Migration will be handled automatically by SQLAlchemy if column doesn't exist
            # This is just a safety check for existing databases
            pass
    
    # Get configuration from environment variables
    host = get_host()
    port = get_port()
    debug = not is_production()
    
    app.run(debug=debug, host=host, port=port)
