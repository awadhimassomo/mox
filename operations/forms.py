from django import forms
from .models import Kijiwe

class KijiweForm(forms.ModelForm):
    class Meta:
        model = Kijiwe
        fields = ['name', 'latitude', 'longitude', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
        }
