import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

export const setAuthToken = (token) => {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common.Authorization;
  }
};

export const login = async (username, password) => {
  const res = await api.post('/auth/login/', { username, password });
  return res.data; // { token }
};

export const signup = async (payload) => {
  const res = await api.post('/auth/signup/', payload);
  return res.data;
};

export const getProfile = async () => {
  const res = await api.get('/auth/get_profile/');
  return res.data;
};

export const updateProfilePhoto = async (file) => {
  const formData = new FormData();
  formData.append('profile_pic', file);

  const res = await api.post('/auth/update_profile_photo/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return res.data;
};

export const getUsers = async () => {
  const res = await api.get('/auth/get_users/');
  return res.data.users;
};

export const getUserGroups = async () => {
  const res = await api.get('/auth/user_groups_from_token/');
  return res.data.groups;
};

export const startDirectChat = async (userId) => {
  const res = await api.post('/auth/start_direct_chat/', { user_id: userId });
  return res.data; // { chat_id, room_name, receiver_id, messages }
};

export const getGroupMessages = async (groupId) => {
  const res = await api.get(`/auth/group_chat_messages/${groupId}/`);
  return res.data; // { group_id, group_name, messages }
};

export const createGroup = async (name) => {
  const res = await api.post('/auth/create_group/', { name });
  return res.data;
};

export const addUsersToGroup = async (groupId, userIds) => {
  const res = await api.post(`/auth/add_user_to_group/${groupId}/`, { user_ids: userIds });
  return res.data;
};

export default api;
