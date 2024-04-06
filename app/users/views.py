from django.contrib.auth import update_session_auth_hash
from django.utils.translation import gettext_lazy as _
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from core.permissions import IsSelfOrReadOnly
from users.models import User
from users.serializers import ChangePasswordSerializer, UserSerializer


class UserListAPIView(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get(self, request, *args, **kwargs):
        available_params = ["username", "email"]
        params = list(filter(lambda param: param[0] in available_params, request.query_params.items()))

        self.queryset = self.queryset.filter(*params)
        return super().get(self, request, *args, **kwargs)


class UserDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsSelfOrReadOnly,)


class UserCurrentAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_queryset(self):
        return self.request.user

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class ChangePasswordAPIView(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            user = request.user

            password = serializer.data.get("password")
            new_password = serializer.data.get("new_password")

            if not user.check_password(password):
                return Response(
                    {
                        "detail": _("Old password is not correct"),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.set_password(new_password)
            user.save()
            update_session_auth_hash(
                request,
                user,
            )
            return Response(
                {"message": _("Password changed successfully")},
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
