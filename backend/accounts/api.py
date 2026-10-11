"""Auth API views: register, login, refresh, me."""
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import CampusTokenSerializer, RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/  -> creates a student account."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # 400 with field errors if invalid
        user = serializer.save()
        # Reply with the safe user view (no password).
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    """POST /api/auth/login/  {username, password} -> {access, refresh, user}"""

    serializer_class = CampusTokenSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class RefreshView(TokenRefreshView):
    """POST /api/auth/refresh/  {refresh} -> {access}"""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class MeView(generics.RetrieveAPIView):
    """GET /api/auth/me/  -> the logged-in user (React uses this after login)."""

    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
