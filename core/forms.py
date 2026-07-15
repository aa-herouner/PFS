from django import forms

from .models import Breed, ExpenseCategory, FeedType, IncomeCategory, Pen

# Tailwind classes applied to text-like inputs, selects and textareas so every
# form in the project shares one look. Include partials/_form_field.html renders
# the label/errors; this mixin styles the widget itself.
INPUT_CLASS = (
    'w-full border border-gray-300 rounded px-3 py-2 text-sm '
    'focus:ring-emerald-500 focus:border-emerald-500'
)
CHECKBOX_CLASS = 'h-4 w-4 text-emerald-600 border-gray-300 rounded focus:ring-emerald-500'


class StyledFormMixin:
    """Adds consistent Tailwind classes to every widget on the form.

    Mix into ModelForm/Form subclasses: `class MyForm(StyledFormMixin, forms.ModelForm)`.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput,)):
                self._add_class(widget, CHECKBOX_CLASS)
            elif isinstance(widget, (forms.RadioSelect, forms.CheckboxSelectMultiple)):
                continue  # rendered as option groups; skip input styling
            else:
                self._add_class(widget, INPUT_CLASS)
            if isinstance(widget, forms.DateInput):
                widget.input_type = 'date'

    @staticmethod
    def _add_class(widget, css):
        existing = widget.attrs.get('class', '')
        widget.attrs['class'] = (existing + ' ' + css).strip()


# --- Reference-data forms --------------------------------------------------

class BreedForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Breed
        fields = ('name', 'bird_type', 'description')


class PenForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Pen
        fields = ('name', 'capacity', 'description')


class FeedTypeForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = FeedType
        fields = ('name', 'category', 'unit', 'unit_cost')


class ExpenseCategoryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ('name',)


class IncomeCategoryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = IncomeCategory
        fields = ('name',)
