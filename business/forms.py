from django import forms
from .models import Product, Business

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name',
            'description',
            'category',
            'unit',
            'price',
            'stock_quantity',
            'gas_type',
            'tank_size',
            'preparation_time',
            'is_vegan',
            'is_halal',
            'image',
            'is_available'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'gas_type': forms.Select(attrs={'class': 'form-control'}),
            'tank_size': forms.Select(attrs={'class': 'form-control'}),
            'preparation_time': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_vegan': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_halal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def __init__(self, *args, **kwargs):
        # Pop the 'business' argument before calling super().__init__
        business = kwargs.pop('business', None)
        super().__init__(*args, **kwargs)
        
        # If you need to use the 'business' instance later in the form, 
        # for example, to filter choices for a ModelChoiceField, you can assign it to self.
        # self.business = business

        # Example: If your category field needed to be filtered by business:
        # if business:
        #     self.fields['category'].queryset = Category.objects.filter(business=business)
        
        # Make category-specific fields optional
        self.fields['gas_type'].required = False
        self.fields['tank_size'].required = False
        self.fields['preparation_time'].required = False
        self.fields['is_vegan'].required = False
        self.fields['is_halal'].required = False
        
        # Add help text
        self.fields['preparation_time'].help_text = 'Time in minutes (for food items only)'
        self.fields['gas_type'].help_text = 'Required for gas products only'
        self.fields['tank_size'].help_text = 'Required for gas products only'
