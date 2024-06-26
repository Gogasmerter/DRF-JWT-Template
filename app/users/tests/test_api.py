from django.test import Client
from django.urls import reverse
import parameterized
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User
from users.serializers import UserSerializer


class UserAPIUrlsTestCase(APITestCase):
    fixtures = ["users/fixtures/test.json"]

    def setUp(self):
        self.user1 = User.objects.get(username="testuser1")
        self.user2 = User.objects.get(username="testuser2")

    def test_list(self):
        url = reverse("users:list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @parameterized.parameterized.expand(
        [
            ("?username=testuser1",),
            ("?email=test1@example.com",),
            ("?email=test1@example.com&username=testuser1",),
        ],
    )
    def test_list_query_params(self, params):
        url = reverse("users:list") + params
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = response.data[0]

        self.assertEqual(user, UserSerializer(self.user1).data)

    def test_detail(self):
        url = reverse("users:detail", kwargs={"pk": self.user1.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], self.user1.username)


class UserAPIPermissionsTestCase(APITestCase):
    fixtures = ["users/fixtures/test.json"]

    def setUp(self):
        self.user1 = User.objects.get(username="testuser")
        self.user2 = User.objects.get(username="testuser2")

        self.client.force_login(self.user1)

    def test_creation(self):
        url = reverse("users:list")
        data = {"username": "testuser3", "email": "test3@example.com", "password": "password123"}
        count = User.objects.count()

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), count + 1)

    def test_valid_retrieve_current_user(self):
        url = reverse("users:my")

        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(UserSerializer(self.user1).data, response.data)

    def test_invalid_retrieve_current_user(self):
        self.client.logout()
        url = reverse("users:my")

        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @parameterized.parameterized.expand(
        [
            (Client().patch, {"username": "111"}),
            (Client().put, {"username": "111", "email": "111@mail.ru"}),
            (Client().delete, {}),
        ],
    )
    def test_invalid(self, method, data):
        self.client.logout()
        url = reverse("users:detail", kwargs={"pk": self.user1.id})

        response = method(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @parameterized.parameterized.expand(
        [
            reverse("users:detail", kwargs={"pk": 2}),
            reverse("users:my"),
        ],
    )
    def test_valid_update_delete(self, url):
        self.client.force_login(self.user1)
        count = User.objects.count()

        data = {"username": "111", "email": "111@mail.ru", "password": "111"}
        response = self.client.put(url, data, format="json")
        user = response.data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(user["username"], "111")
        self.assertEqual(user["email"], "111@mail.ru")

        data = {"username": "testuser", "password": "111"}
        response = self.client.patch(url, data, format="json")
        user = response.data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(user["username"], "testuser")

        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(User.objects.count(), count - 1)

    def test_invalid_update_delete(self):
        self.client.force_login(self.user1)
        url = reverse("users:detail", kwargs={"pk": self.user2.id})

        data = {"username": "111", "email": "111@mail.ru", "password": "password123"}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        data = {"username": "testuser"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ChangePasswordAPITestCase(APITestCase):
    fixtures = ["users/fixtures/test.json"]

    def setUp(self):
        self.user = User.objects.get(username="testuser")

    def test_valid(self):
        self.client.force_login(self.user)
        url = reverse("users:change_password")
        data = {"password": "111", "new_password": "new_password123", "new_password_confirm": "new_password123"}

        response = self.client.post(url, data, format="json")
        self.user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.user.check_password("new_password123"))

    @parameterized.parameterized.expand(
        [
            ({},),
            ({"password": "222", "new_password": "password123", "new_password_confirm": "password123"},),
            (
                {
                    "password": "111",
                    "new_password": "new_password321",
                    "new_password_confirm": "new_password123",
                },
            ),
        ],
    )
    def test_invalid(self, data):
        self.client.force_login(self.user)
        url = reverse("users:change_password")
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
