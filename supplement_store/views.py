from django.shortcuts import redirect, render, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.decorators import login_required

from .models import User

# Create your views here.

def index(request):
    return render(request, "supplement_store/index.html")

def login_view(request):
    if request.method == 'POST':
        first = request.POST["first"]
        password = request.POST["password"]

        if '@' in first:
            user = authenticate(request, email=first, password=password)
        else:
            user = authenticate(request, username=first, password=password)

        if user is not None:
            login(request, user)
            return redirect('index')
        else:
            messages.error(request, "Invalid login credentials. Please try again.")
            return redirect('login')
        
    return render(request, "supplement_store/login.html")

def register_view(request):
    if request.method == 'POST':
        email = request.POST["email"]
        username = request.POST["username"]
        first = request.POST["first"]
        last = request.POST["last"]
        phone = request.POST["phone"]
        birthday = request.POST["birthday"]
        address = request.POST["address"]
        city = request.POST["city"]
        state = request.POST["state"]
        country = request.POST["country"]
        zipcode = request.POST["zipcode"]
        password = request.POST["password"]
        confirm_password = request.POST["confirm-password"]
        if password != confirm_password:
            messages.error(request, "Passwords do not match. Please try again.")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email address already taken.")
            return redirect("register")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect("register")
        
        user = User.objects.create_user(username=username, email=email, password=password, first_name=first, last_name=last, phone=phone, birth=birthday, address=address, city=city, state=state, country=country, zipcode=zipcode)
        user.is_active = False
        user.save()

        #emailing logic
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

        return HttpResponse("Your account is being activated. Please wait... <br> Check your email inbox and spam folder.")
    return render(request, "supplement_store/register.html")

def activate_email(request, uidb64, token):
    try:
        uid = force_bytes(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except User.DoesNotExist:
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        print(user)
        user.save()
        
        login(request, user)
        return redirect('index')
    return redirect('register')

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