from ninja_extra import NinjaExtraAPI
from ninja_jwt.controller import NinjaJWTDefaultController
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
import random
from datetime import date, timedelta

from .models import CustomUser, Canteen, NGO, Record, Alter, RE
from .schemas import *

api = NinjaExtraAPI(
    title="Food Waste Prediction & Redistribution API",
    version="1.0.0",
    description="Production-ready backend for canteen surplus prediction & NGO redistribution"
)

# Register built-in JWT endpoints: /api/token/obtain , /token/refresh , /token/verify
api.register_controllers(NinjaJWTDefaultController)

User = get_user_model()

# ====================== AUTH ======================
@api.post("/auth/signup", auth=None, response={201: dict, 400: dict})
def signup(request, data: SignUpSchema):
    if data.role not in ['canteen_admin', 'ngo']:
        return 400, {"error": "Only Canteen Admin or NGO can signup"}

    if User.objects.filter(username=data.username).exists():
        return 400, {"error": "Username already taken"}

    user = User.objects.create_user(
        username=data.username,
        email=data.email,
        password=data.password,
        role=data.role
    )

    if data.role == 'canteen_admin':
        Canteen.objects.create(
            user=user,
            name=data.canteen_name or f"Canteen-{data.username}",
            location=data.canteen_location or "Default Location"
        )
    elif data.role == 'ngo':
        NGO.objects.create(
            user=user,
            name=data.ngo_name or f"NGO-{data.username}",
            address=data.ngo_address or "",
            contact_person=data.ngo_contact_person or data.username,
            phone=data.ngo_phone or ""
        )

    # Return token immediately
    refresh = RefreshToken.for_user(user)
    return 201, {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {"id": user.id, "username": user.username, "role": user.role}
    }

# Login is handled by built-in /api/token/obtain (username + password)

@api.post("/auth/logout", auth=JWTAuth())
def logout(request):
    # Blacklist current token (django-ninja-jwt supports it)
    try:
        refresh = RefreshToken(request.auth.raw_token)  # raw_token from request
        refresh.blacklist()
    except:
        pass
    return {"message": "Successfully logged out"}

# ====================== USER PROFILE ======================
@api.get("/profile", auth=JWTAuth(), response=UserProfileOut)
def get_profile(request):
    user = request.auth
    profile = {"id": user.id, "username": user.username, "email": user.email, "role": user.role}
    if user.role == 'canteen_admin' and hasattr(user, 'canteen_profile'):
        c = user.canteen_profile
        profile['canteen'] = {"id": c.id, "name": c.name, "location": c.location}
    elif user.role == 'ngo' and hasattr(user, 'ngo_profile'):
        n = user.ngo_profile
        profile['ngo'] = {"id": n.id, "name": n.name}
    return profile

@api.patch("/profile", auth=JWTAuth())
def update_profile(request, data: dict):  # flexible dict for simplicity
    user = request.auth
    if 'email' in data:
        user.email = data['email']
    user.save()

    if user.role == 'canteen_admin' and hasattr(user, 'canteen_profile'):
        canteen = user.canteen_profile
        if 'name' in data: canteen.name = data['name']
        if 'location' in data: canteen.location = data['location']
        canteen.save()
    elif user.role == 'ngo' and hasattr(user, 'ngo_profile'):
        ngo = user.ngo_profile
        if 'name' in data: ngo.name = data['name']
        ngo.save()
    return {"message": "Profile updated successfully"}

# ====================== RECORD APIs ======================
@api.post("/records", auth=JWTAuth())
def create_record(request, payload: RecordIn):
    user = request.auth
    if user.role != 'canteen_admin' or not hasattr(user, 'canteen_profile'):
        return 403, {"error": "Only Canteen Admin can create records"}
    
    canteen = user.canteen_profile
    record = Record.objects.create(
        canteen=canteen,
        date=payload.date,
        day=payload.day,
        meal_menu_info=payload.meal_menu_info,
        cooked=payload.cooked,
        surplus=payload.surplus,
        no_members=payload.no_members
    )
    return {"id": record.id, "message": "Record created"}

@api.get("/records", auth=JWTAuth())
def list_records(request, date_from: Optional[date] = None, date_to: Optional[date] = None):
    user = request.auth
    qs = Record.objects.select_related('canteen')

    if user.role == 'canteen_admin' and hasattr(user, 'canteen_profile'):
        qs = qs.filter(canteen=user.canteen_profile)
    elif user.role == 'superadmin':
        pass  # all records
    else:
        return 403, {"error": "Not allowed"}

    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)

    return list(qs.values('id', 'date', 'day', 'cooked', 'surplus', 'no_members', 'canteen__name'))

# ====================== DUMMY PREDICTION APIs (random fake data) ======================
@api.get("/predict/footfall", auth=JWTAuth(), response=PredictionOut)
def predict_footfall(request, target_date: Optional[date] = None):
    """Dummy time-series prediction - returns random but realistic fake data"""
    if not target_date:
        target_date = date.today() + timedelta(days=1)
    
    # Simulate realistic numbers based on historical average logic
    base_footfall = random.randint(800, 2500)
    predicted_footfall = base_footfall + random.randint(-200, 300)
    predicted_surplus = max(0, int(predicted_footfall * 0.12))  # ~12% surplus assumption

    return {
        "predicted_footfall": predicted_footfall,
        "predicted_surplus": predicted_surplus,
        "confidence": round(random.uniform(0.78, 0.95), 2),
        "date": target_date
    }

@api.get("/predict/surplus", auth=JWTAuth(), response=PredictionOut)
def predict_surplus(request, target_date: Optional[date] = None):
    """Same dummy engine - used by canteen for surplus estimation"""
    if not target_date:
        target_date = date.today() + timedelta(days=1)
    data = predict_footfall(request, target_date)  # reuse logic
    data["predicted_footfall"] = data["predicted_footfall"]  # keep same format
    return data

# ====================== REINFORCEMENT (optional) ======================
@api.post("/re", auth=JWTAuth())
def create_re(request, date: date, model_predict: int, actual: int):
    user = request.auth
    if user.role != 'canteen_admin' or not hasattr(user, 'canteen_profile'):
        return 403, {"error": "Only Canteen Admin"}
    RE.objects.create(
        canteen=user.canteen_profile,
        date=date,
        model_predict=model_predict,
        actual_data=actual
    )
    return {"message": "RE feedback recorded for model improvement"}

# ====================== ALTER + NGO REQUEST FOOD ======================
@api.post("/alters", auth=JWTAuth())
def create_alter(request, date: date, start_time: time, end_time: time,
                 quantity: int, meal_type: str, notes: Optional[str] = None):
    user = request.auth
    if user.role != 'canteen_admin' or not hasattr(user, 'canteen_profile'):
        return 403, {"error": "Only Canteen Admin can create Alter"}
    alter = Alter.objects.create(
        canteen=user.canteen_profile,
        date=date,
        start_time=start_time,
        end_time=end_time,
        quantity=quantity,
        meal_type=meal_type,
        notes=notes or ""
    )
    return {"id": alter.id, "message": "Alter (spoiled food alert) created"}

@api.get("/alters", auth=JWTAuth())
def list_alters(request):
    """NGOs can see all active alters for redistribution"""
    return list(Alter.objects.select_related('canteen').values(
        'id', 'date', 'start_time', 'end_time', 'quantity', 'meal_type', 'canteen__name'
    ))

@api.post("/request-food", auth=JWTAuth())
def request_food_after_alter(request, payload: AlterRequestSchema):
    """NGO requests surplus/spoiled food after Alter is kicked off"""
    user = request.auth
    if user.role != 'ngo':
        return 403, {"error": "Only NGO can request food"}

    alter = get_object_or_404(Alter, id=payload.alter_id)
    # In real system you would create a Request model + notification + logistics
    # For now we just acknowledge the request
    return {
        "message": f"Request received from {user.username} for Alter #{alter.id} "
                   f"({alter.quantity} {alter.meal_type} from {alter.canteen.name})",
        "status": "PENDING",
        "ngo": user.username,
        "alter_id": alter.id
    }