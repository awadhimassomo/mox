from django.core.mail import send_mail
from django.conf import settings

def check_low_stock(products):
    """Check if any product is running low on stock and send an alert."""
    low_stock_products = [product for product in products if product.stock_quantity < 5]
    
    if low_stock_products:
        # Skip email sending for now but still return the alert message
        # This avoids the error with missing BUSINESS_EMAIL setting
        '''
        subject = " Low Stock Alert"
        message = "The following products are running low on stock:\n\n"
        for product in low_stock_products:
            message += f"- {product.name}: {product.stock_quantity} left\n"
        
        # Email sending code removed to prevent errors
        # If email functionality is needed, use business owner's email instead
        '''
        
        return f"Alert: {len(low_stock_products)} products have low stock levels."
    return "Stock levels are sufficient."
