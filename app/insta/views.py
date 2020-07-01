from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from . import models

from .serializers import UserListSerializer, UserRetrieveSerializer, MediaSerializer

from .instagram import API

User = get_user_model()


def complete(request):
    code = request.GET['code']
    unique_id = request.GET.get('state', None)
    api = API()
    user_id = api.get_user_cache(unique_id)
    if user_id is not None:
        user = User.objects.get(id=int(user_id))
        api.get_insta_account(user, code)
        return redirect(reverse('user-instagram', kwargs={'pk': user_id}))
    return redirect('/')


@csrf_exempt
def delete(request):
    api = API()
    api.destroy(request.POST['signed_request'])
    return redirect('/')


class UserViewSet(viewsets.ModelViewSet):
    api = API()
    queryset = User.objects.all()
    serializer_class = UserRetrieveSerializer
    serializer_action_classes = {
        'list': UserListSerializer,
    }

    def get_serializer_class(self):
        try:
            return self.serializer_action_classes[self.action]
        except (KeyError, AttributeError):
            return super().get_serializer_class()

    @action(detail=True, methods=['get', 'post', 'delete'])
    def instagram(self, request, *args, **kwargs):
        if request.method == 'GET':
            user = self.get_object()
            try:
                access_token = user.instagram.access_token
                user_media = self.api.get_user_media(user.instagram.data['id'], access_token)
                media = [self.api.get_media_fields(row, access_token) for row in user_media[:10]]
                serializer = MediaSerializer(media, many=True)
                return Response(serializer.data)
            except models.User.instagram.RelatedObjectDoesNotExist:
                return Response([])
        elif request.method == 'POST':
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            # return redirect(self.api.get_authorize_uri(user_id=self.kwargs[lookup_url_kwarg]))
            return Response({'url': self.api.get_authorize_uri(user_id=self.kwargs[lookup_url_kwarg])})
        elif request.method == 'DELETE':
            user = self.get_object()
            user.instagram.delete()
        return Response({})
