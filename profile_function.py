@login_required
def profile(request):
    """View to display and update user profile information"""
    try:
        # Check if user has a customer profile
        if not hasattr(request.user, 'customer_profile'):
            # Create a customer profile for the user if it doesn't exist
            from customers.models import CustomerProfile
            customer = CustomerProfile.objects.create(
                user=request.user,
                phone_number=f"temp_{request.user.id}"  # Temporary phone number
            )
        else:
            customer = request.user.customer_profile
            
        # Initialize form with user data
        if request.method == 'POST':
            form = CustomerProfileForm(request.POST, request.FILES, instance=customer)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile updated successfully.')
                return redirect('customers:profile')
        else:
            form = CustomerProfileForm(instance=customer)
        
        # Get user orders for profile view
        orders = Order.objects.filter(customer=customer).order_by('-created_at')[:5]
        addresses = DeliveryAddress.objects.filter(customer=customer)
        favorite_businesses = Favorite.objects.filter(customer=customer).select_related('business')
        
        context = {
            'profile_form': form,
            'customer': customer,
            'recent_orders': orders,
            'addresses': addresses,
            'favorite_businesses': favorite_businesses,
        }
        
        return render(request, 'customers/profile.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading profile: {str(e)}')
        return redirect('customers:home')
