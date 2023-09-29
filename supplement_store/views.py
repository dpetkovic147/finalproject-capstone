from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.contrib.auth.forms import SetPasswordForm
from django.http import JsonResponse
from django.db.models import Subquery, OuterRef, F

from datetime import datetime

from .forms import RegistrationForm
from .countries import COUNTRIES
from .models import User, SlideShowImage, Support, SupportAnswer

# Create your views here.

def index(request):
    return render(request, "supplement_store/index.html", {
        "images": SlideShowImage.objects.all().order_by('-order'),
    })

@login_required
def chatting(request):
    if request.method == 'POST':
        message = request.POST.get('text-field', '')
        if message:
            Support.objects.create(user=request.user, message=message, date=datetime.now())
            return JsonResponse({'success': 'Message saved to the database'})
        else:
            return JsonResponse({'error': 'Message is empty'}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@login_required
def inbox(request):
    if request.user.is_staff == True:
        latest_message_subquery = Support.objects.filter(user=OuterRef('user')).order_by('-date').values('message')[:1]
        one_message_per_user = Support.objects.annotate(latest_message=Subquery(latest_message_subquery)).filter(message=F('latest_message'))
        messages = one_message_per_user.all()
        return render(request, "supplement_store/inbox.html", {
            "messages": messages
        })
    else: 
        return redirect('index')

@login_required
def answer_inbox(request, username):
    if request.user.is_staff == True:
        user = User.objects.get(username=username)
        messages = Support.objects.filter(user=user).order_by('-date')
        answers = SupportAnswer.objects.filter(latest_message=Support.objects.filter(user=user).order_by('-date').first()).order_by('-date')
        print(f"answer_inbox {answers}")
        return render(request, "supplement_store/answer_inbox.html", {
            "messages": messages,
            "answers": answers
        })
    else: 
        return redirect('index')

@login_required
def answering(request, username):
    if request.user.is_staff == True:
        user = User.objects.get(username=username)
        response = request.POST["text"]
        answers = SupportAnswer.objects.create(response=response, latest_message=Support.objects.filter(user=user).order_by('-date').first(), date=datetime.now())
        print(f"answering {answers}")
        return redirect('answer_inbox', username=user.username)
    else: 
        return redirect('index')    
    

@login_required
def get_chat_messages_view(request):
    if request.method == 'GET':
        messages = Support.objects.filter(user=request.user).order_by('date')
        formatted_messages = [{'user': message.user.username, 'message': message.message} for message in messages]
        return JsonResponse({'messages': formatted_messages})
    return JsonResponse({'error': 'Invalid request method'}, status=400)

def login_view(request):
    if request.method == 'POST':
        first = request.POST.get("first")
        password = request.POST.get("password")
        remember = request.POST.get("remember")

        if '@' in first:
            user = authenticate(request, email=first, password=password)
        else:
            user = authenticate(request, username=first, password=password)

        if user is not None:
            if remember:
                user.remember_me = True
                user.save()
                request.session.set_expiry(1209600)
                request.session.modified = True
            else:
                user.remember_me = False
                user.save()
                request.session.set_expiry(0)
                request.session.modified = True
            login(request, user)
            return redirect('index')
        else:
            messages.error(request, "Invalid login credentials. Please try again.")
            return redirect('login_view')
        
    return render(request, "supplement_store/login.html")

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)

        if form.is_valid():
        # get the info from the user
            email = form.cleaned_data["email"]
            username = form.cleaned_data["username"]
            first = form.cleaned_data["first_name"]
            last = form.cleaned_data["last_name"]
            phone = form.cleaned_data["phone"]
            birthday = form.cleaned_data["birthday"]
            address = form.cleaned_data["address"]
            city = form.cleaned_data["city"]
            state = form.cleaned_data["state"]
            country = request.POST["country"]
            zipcode = form.cleaned_data["zipcode"]
            password = form.cleaned_data["password"]
            confirm_password = form.cleaned_data["confirm_password"]
            captcha = form.cleaned_data["captcha"]

            # napraviti provere (ima u django vec napravljene premade)

            # create the user
            user = User.objects.create_user(username=username, email=email, password=password, first_name=first, last_name=last, phone=phone, birth=birthday, address=address, city=city, state=state, country=country, zipcode=zipcode)
            user.is_active = False
            user.save()

            # emailing logic
            mail_subject = "Activate your user account."
            message = render_to_string("supplement_store/confirmation_email.html", {
                "user": user.username,
                "domain": get_current_site(request).domain,
                "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                "token": default_token_generator.make_token(user),
                "protocol": 'https' if request.is_secure() else 'http'
            })
            email = EmailMessage(mail_subject, message, to=[email])
            email.send()

            return render(request, "supplement_store/loading.html")
    else:
        form = RegistrationForm()
    return render(request, "supplement_store/register.html", {
        "countries": [(code, name) for code, name in COUNTRIES.items()],
        "form": form
    })

def activate_email(request, uidb64, token):
    try:
        uid = force_bytes(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except User.DoesNotExist:
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        
        login(request, user)
        return redirect('index')
    return redirect('register_view')

@login_required
def logout_view(request):
    logout(request)
    return redirect('index')

@login_required
def account(request):
    return render(request, "supplement_store/account.html")

def reset_password(request):
    return render(request, "supplement_store/reset_password.html")

@login_required
def wishlist(request):
    return render(request, "supplement_store/wishlist.html")

def shopping_cart(request):
    return render(request, "supplement_store/cart.html")

def newsletter(request):
    return redirect(request.META.get('HTTP_REFERER', 'index'))

def about(request):
    return render(request, "supplement_store/about.html")

def brands(request):
    return render(request, "supplement_store/brands.html")

def contact(request):
    return render(request, "supplement_store/contact.html")

class CustomPasswordResetView(PasswordResetView):
    def form_valid(self, form):
        email = form.cleaned_data['email']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            form.add_error('email', 'Email does not exist.')
            return self.form_invalid(form)
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('password_reset_done')
    
class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = SetPasswordForm

    def form_valid(self, form):
        password1 = form.cleaned_data['new_password1']
        password2 = form.cleaned_data['new_password2']

        if password1 != password2:
            form.add_error('new_password2', 'Passwords do not match')
            return self.form_invalid(form)

        response = super().form_valid(form)

        update_session_auth_hash(self.request, self.request.user)

        return response