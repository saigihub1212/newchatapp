import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import './App.css';
import {
  login as loginApi,
  signup as signupApi,
  getProfile,
  getUsers,
  getUserGroups,
  startDirectChat,
  getGroupMessages,
  setAuthToken,
  createGroup as createGroupApi,
  addUsersToGroup,
  updateProfilePhoto,
} from './api';

const WS_BASE = 'ws://127.0.0.1:8000';

function App() {
  const [token, setToken] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const currentUserRef = useRef(null);
  const [authError, setAuthError] = useState('');
  const [loadingAuth, setLoadingAuth] = useState(false);
  const [authMode, setAuthMode] = useState('login'); // 'login' | 'signup'

  const [users, setUsers] = useState([]);
  const [groups, setGroups] = useState([]);

  const [userSearch, setUserSearch] = useState('');

  const [activeChat, setActiveChat] = useState(null); // {type: 'direct'|'group', id, name}
  const [messages, setMessages] = useState([]);
  const [connecting, setConnecting] = useState(false);
  const [ws, setWs] = useState(null);
  const [notifWs, setNotifWs] = useState(null);
  const [toasts, setToasts] = useState([]);
  const [unreadCounts, setUnreadCounts] = useState({}); // keys: 'user_<id>' or 'group_<id>'

  const [composerText, setComposerText] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  const incrUnread = (key) => setUnreadCounts((prev) => ({ ...prev, [key]: (prev[key] || 0) + 1 }));
  const clearUnreadKey = (key) => setUnreadCounts((prev) => { const p = { ...prev }; delete p[key]; return p; });

  const showToast = useCallback((payload) => {
    const id = `toast_${Date.now()}_${Math.random().toString(36).slice(2,8)}`;
    const toast = { id, ...payload };
    setToasts((prev) => [...prev, toast]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const clearToast = (id) => setToasts((prev) => prev.filter((t) => t.id !== id));

  const openFromToast = async (userId, toastId, chatId) => {
    clearToast(toastId);
    // try to find user object in memory
    const user = users.find((u) => Number(u.id) === Number(userId));
    if (user) {
      await openDirectChat(user);
      return;
    }

    // fallback: ask server to start a direct chat and open it
    try {
      const data = await startDirectChat(userId);
      setActiveChat({ type: 'direct', id: data.chat_id, name: data.username || '' });
      setMessages(data.messages || []);
      connectWebSocket('direct', data.chat_id);
    } catch (err) {
      console.error('Failed to open chat from toast', err);
    }
  }; 

  // Profile / settings view
  const [showProfile, setShowProfile] = useState(false);

  const [updatingProfile, setUpdatingProfile] = useState(false);
  const [profileError, setProfileError] = useState('');

  // Create group modal
  const [showCreateGroup, setShowCreateGroup] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [selectedMembers, setSelectedMembers] = useState([]);

  // Chat type tab (Private / Groups)
  const [chatTab, setChatTab] = useState('private'); // 'private' | 'groups'

  // Track recent chat activity for sorting
  const [recentChats, setRecentChats] = useState({}); // { 'direct_123': timestamp, 'group_456': timestamp }

  // Keep ref in sync with currentUser for WebSocket callbacks
  useEffect(() => {
    currentUserRef.current = currentUser;
  }, [currentUser]);

  const isAuthenticated = useMemo(() => !!token && !!currentUser, [token, currentUser]);

  // Filter users to exclude current user and sort by recent activity
  const filteredUsers = useMemo(() => {
    let filtered = users;

    if (currentUser) {
      filtered = filtered.filter((u) => Number(u.id) !== Number(currentUser.id));
    }

    if (userSearch.trim()) {
      const q = userSearch.trim().toLowerCase();
      filtered = filtered.filter((u) => u.username.toLowerCase().includes(q));
    }
    // Sort by recent activity (users with recent direct chats first)
    return filtered.sort((a, b) => {
      const aTime = recentChats[`user_${a.id}`] || 0;
      const bTime = recentChats[`user_${b.id}`] || 0;
      return bTime - aTime; // Most recent first
    });
  }, [users, currentUser, recentChats, userSearch]);

  // Sort groups by recent activity
  const sortedGroups = useMemo(() => {
    return [...groups].sort((a, b) => {
      const aTime = recentChats[`group_${a.id}`] || 0;
      const bTime = recentChats[`group_${b.id}`] || 0;
      return bTime - aTime;
    });
  }, [groups, recentChats]);

  // LOGOUT ----------------------------------------------------
  const handleLogout = () => {
    setToken(null);
    setAuthToken(null);
    try {
      window.localStorage.removeItem('authToken');
    } catch (e) {
      // ignore storage errors
    }
    setCurrentUser(null);
    setUsers([]);
    setGroups([]);
    setActiveChat(null);
    setMessages([]);
    if (ws) {
      ws.close();
      setWs(null);
    }
    if (notifWs) {
      notifWs.close();
      setNotifWs(null);
    }
    setShowProfile(false);
  };

  // CREATE GROUP ----------------------------------------------
  const handleCreateGroup = async () => {
    if (!newGroupName.trim()) return;
    try {
      const result = await createGroupApi(newGroupName.trim());
      const newGroup = { id: result.group_id, name: result.group_name };
      
      // Add selected members to the group
      if (selectedMembers.length > 0) {
        try {
          await addUsersToGroup(result.group_id, selectedMembers);
        } catch (err) {
          console.error('Failed to add members to group', err);
        }
      }
      
      setGroups((prev) => [...prev, newGroup]);
      setNewGroupName('');
      setSelectedMembers([]);
      setShowCreateGroup(false);
    } catch (err) {
      console.error('Failed to create group', err);
    }
  };

  const toggleMemberSelection = (userId) => {
    setSelectedMembers((prev) =>
      prev.includes(userId)
        ? prev.filter((id) => id !== userId)
        : [...prev, userId]
    );
  };

  // AUTH ------------------------------------------------------
  const handleLogin = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const username = formData.get('username');
    const password = formData.get('password');

    setAuthError('');
    setLoadingAuth(true);
    try {
      const { token: jwt } = await loginApi(username, password);
      setToken(jwt);
      setAuthToken(jwt);
      try {
        window.localStorage.setItem('authToken', jwt);
      } catch (e) {
        // ignore storage errors
      }
      const profile = await getProfile();
      setCurrentUser(profile);
    } catch (err) {
      setAuthError(err?.response?.data?.error || 'Login failed');
      setToken(null);
      setAuthToken(null);
    } finally {
      setLoadingAuth(false);
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const username = formData.get('username');
    const password = formData.get('password');
    const age = formData.get('age');
    const gender = formData.get('gender');

    setAuthError('');
    setLoadingAuth(true);
    try {
      await signupApi({
        username,
        password,
        age,
        gender,
      });

      // Auto-login after successful signup
      const { token: jwt } = await loginApi(username, password);
      setToken(jwt);
      setAuthToken(jwt);
      try {
        window.localStorage.setItem('authToken', jwt);
      } catch (e) {
        // ignore storage errors
      }
      const profile = await getProfile();
      setCurrentUser(profile);
    } catch (err) {
      let message = 'Signup failed';

      if (err?.response) {
        const { data } = err.response;
        if (data && typeof data === 'object') {
          // DRF validation errors – flatten into a simple string
          const parts = [];
          Object.entries(data).forEach(([field, value]) => {
            if (Array.isArray(value)) {
              parts.push(`${field}: ${value.join(' ')}`);
            } else {
              parts.push(`${field}: ${value}`);
            }
          });
          if (parts.length) {
            message = parts.join(' | ');
          }
        } else if (typeof data === 'string') {
          message = data;
        }
      } else if (err?.request) {
        message = 'Network error. Cannot reach backend server.';
      }

      setAuthError(message);
      setToken(null);
      setAuthToken(null);
    } finally {
      setLoadingAuth(false);
    }
  };

  // On first load, restore token from localStorage and fetch profile
  useEffect(() => {
    let stored = null;
    try {
      stored = window.localStorage.getItem('authToken');
    } catch (e) {
      stored = null;
    }

    if (!stored) return;

    setToken(stored);
    setAuthToken(stored);

    const loadProfile = async () => {
      try {
        const profile = await getProfile();
        setCurrentUser(profile);
      } catch (err) {
        // invalid/expired token; clear it
        setToken(null);
        setAuthToken(null);
        try {
          window.localStorage.removeItem('authToken');
        } catch (e) {
          // ignore
        }
      }
    };

    loadProfile();
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;

    const fetchData = async () => {
      try {
        const [usersData, groupsData] = await Promise.all([
          getUsers(),
          getUserGroups(),
        ]);
        setUsers(usersData);
        setGroups(groupsData);
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error('Failed to load sidebar data', err);
      }
    };

    fetchData();
  }, [isAuthenticated]);

  // Notifications WebSocket — keep a lightweight connection for user-level events
  useEffect(() => {
    if (!isAuthenticated) return;

    // request native Notification permission once (graceful)
    if (typeof Notification !== 'undefined' && Notification.permission === 'default') {
      try { Notification.requestPermission(); } catch (e) { /* ignore */ }
    }

    const url = `${WS_BASE}/ws/notifications/?token=${token}`;
    const socket = new WebSocket(url);

    socket.onopen = () => {
      console.debug('Notifications WS connected', url);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.debug('Notifications WS message', data);

        // someone added you to a group
        if (data.event === 'group_added' || data.type === 'group.added') {
          setGroups((prev) => {
            if (prev.some((g) => g.id === data.group_id)) return prev;
            return [...prev, { id: data.group_id, name: data.group_name }];
          });
          setRecentChats((prev) => ({ ...prev, [`group_${data.group_id}`]: Date.now() }));
          showToast({ title: 'Added to group', body: data.group_name || 'New group', chatId: data.group_id });
          return;
        }

        // incoming direct message notification — bump recent-activity for sender
        if (data.event === 'message_received' || data.type === 'message.received') {
          const senderId = data.sender_id != null ? Number(data.sender_id) : null;
          setRecentChats((prev) => ({ ...prev, [`user_${senderId}`]: Date.now() }));

          // if recipient is NOT viewing that chat, increment unread counter
          if (!(activeChat?.type === 'direct' && Number(activeChat?.id) === Number(data.chat_id))) {
            if (senderId != null) {
              setUnreadCounts((prev) => ({ ...prev, [`user_${senderId}`]: (prev[`user_${senderId}`] || 0) + 1 }));
            }
          }

          // don't show popup if user is currently viewing that direct chat
          if (activeChat?.type === 'direct' && Number(activeChat?.id) === Number(data.chat_id)) {
            return;
          }

          // show in-app toast
          showToast({ title: data.sender || 'New message', body: data.text || '', userId: senderId, chatId: data.chat_id });

          // native browser notification
          if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
            try {
              const n = new Notification(data.sender || 'New message', { body: data.text || '' });
              n.onclick = () => { window.focus(); };
            } catch (e) { /* ignore */ }
          }
        }
      } catch (err) {
        console.error('Failed to parse notifications WS message', err);
      }
    };

    socket.onclose = () => {
      console.debug('Notifications WS closed');
      setNotifWs(null);
    };

    setNotifWs(socket);

    return () => {
      socket.close();
      setNotifWs(null);
    };
  }, [isAuthenticated, token, activeChat, showToast]); 

  // CHAT SELECTION & MESSAGE LOADING --------------------------
  const resetChatState = () => {
    setMessages([]);
    setComposerText('');
    if (ws) {
      ws.close();
      setWs(null);
    }
  };

  const openDirectChat = async (user) => {
    if (!isAuthenticated) return;
    resetChatState();
    setActiveChat({ type: 'direct', id: null, name: user.username, raw: user });
    setConnecting(true);
    // Track recent activity
    setRecentChats((prev) => ({ ...prev, [`user_${user.id}`]: Date.now() }));
    try {
      const data = await startDirectChat(user.id);
      setActiveChat({ type: 'direct', id: data.chat_id, name: user.username, raw: user });
      setMessages(data.messages || []);
      // clear unread for this user/chat
      setUnreadCounts((prev) => { const p = { ...prev }; delete p[`user_${user.id}`]; return p; });
      connectWebSocket('direct', data.chat_id);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('Failed to open direct chat', err);
    } finally {
      setConnecting(false);
    }
  };

  const openGroupChat = async (group) => {
    if (!isAuthenticated) return;
    resetChatState();
    setActiveChat({ type: 'group', id: group.id, name: group.name, raw: group });
    setConnecting(true);
    // Track recent activity
    setRecentChats((prev) => ({ ...prev, [`group_${group.id}`]: Date.now() }));
    try {
      const data = await getGroupMessages(group.id);
      setMessages(data.messages || []);
      // clear unread for this group/chat
      setUnreadCounts((prev) => { const p = { ...prev }; delete p[`group_${group.id}`]; return p; });
      connectWebSocket('group', group.id);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('Failed to open group chat', err);
    } finally {
      setConnecting(false);
    }
  };

  // WEBSOCKET HANDLING ----------------------------------------
  const connectWebSocket = (type, id) => {
    if (!token) return;
    const url =
      type === 'direct'
        ? `${WS_BASE}/ws/chat/direct/${id}/?token=${token}`
        : `${WS_BASE}/ws/chat/group/${id}/?token=${token}`;

    const socket = new WebSocket(url);
    setWs(socket);

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'chat.message' || data.text) {
          const incomingSenderId = data.sender_id != null ? Number(data.sender_id) : null;
          const myId = currentUserRef.current?.id != null ? Number(currentUserRef.current.id) : null;

          // clear unread for this chat because user is viewing it
          if (type === 'direct' && incomingSenderId != null) {
            setUnreadCounts((prev) => { const p = { ...prev }; delete p[`user_${incomingSenderId}`]; return p; });
          } else if (type === 'group') {
            setUnreadCounts((prev) => { const p = { ...prev }; delete p[`group_${id}`]; return p; });
          }

          setMessages((prev) => {
            // Check if we have an optimistic message with same text (for dedup)
            const optimisticIdx = prev.findIndex(
              (msg) => msg._optimistic && msg.text === data.text
            );
            
            if (optimisticIdx !== -1) {
              // Replace optimistic message with confirmed one
              const updated = [...prev];
              updated[optimisticIdx] = {
                id: data.id || Date.now(),
                sender_id: incomingSenderId,
                sender: data.sender || '',
                text: data.text,
                created_at: data.created_at,
              };
              return updated;
            }
            
            // Check if message already exists (by id)
            if (data.id && prev.some((msg) => msg.id === data.id)) {
              return prev; // Skip duplicate
            }
            
            // New message from someone else (or echo without optimistic)
            return [
              ...prev,
              {
                id: data.id || Date.now(),
                sender_id: incomingSenderId,
                sender: data.sender || '',
                text: data.text,
                created_at: data.created_at,
              },
            ];
          });
        }
      } catch (err) {
        console.error('Failed to parse WS message', err);
      }
    };

    socket.onclose = () => {
      setWs(null);
    };
  };

  const handleSend = () => {
    if (!ws || !composerText.trim()) return;
    const text = composerText.trim();

    // Optimistic UI: add message immediately so it appears on the right
    const optimisticMsg = {
      id: `optimistic-${Date.now()}`,
      sender_id: currentUser?.id != null ? Number(currentUser.id) : null,
      sender: currentUser?.username || '',
      text,
      created_at: new Date().toISOString(),
      _optimistic: true, // marker for deduplication
    };
    setMessages((prev) => [...prev, optimisticMsg]);

    ws.send(JSON.stringify({ text }));
    setComposerText('');
  };

  const handleProfilePicChange = async (event) => {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    setProfileError('');
    setUpdatingProfile(true);
    try {
      const data = await updateProfilePhoto(file);
      setCurrentUser((prev) => (
        prev
          ? {
              ...prev,
              profile_pic_url: data.profile_pic_url,
            }
          : prev
      ));
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('Failed to update profile photo', err);
      setProfileError('Failed to update profile photo');
    } finally {
      setUpdatingProfile(false);
      event.target.value = '';
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="app-root app-root--auth">
        <div className="auth-card">
          <div className="auth-title">
            {authMode === 'login' ? 'Welcome back' : 'Create Account'}
          </div>
          <div className="auth-subtitle">
            {authMode === 'login' ? 'Please enter your account details' : 'Fill in your details to get started'}
          </div>
          <form
            className="auth-form"
            onSubmit={authMode === 'login' ? handleLogin : handleSignup}
          >
            <div className="auth-field">
              <label htmlFor="username">Username</label>
              <input
                id="username"
                name="username"
                type="text"
                placeholder="Enter your username"
                autoComplete="username"
                required
              />
            </div>
            <div className="auth-field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                name="password"
                type="password"
                placeholder="••••••••"
                autoComplete="current-password"
                required
              />
            </div>
            {authMode === 'signup' && (
              <>
                <div className="auth-field">
                  <label htmlFor="age">Age</label>
                  <input
                    id="age"
                    name="age"
                    type="number"
                    min="1"
                    placeholder="Enter age"
                    required
                  />
                </div>
                <div className="auth-field">
                  <label htmlFor="gender">Gender</label>
                  <select id="gender" name="gender" required className="auth-select">
                    <option value="" disabled selected hidden>
                      Select gender
                    </option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </>
            )}
            {authError && <div className="auth-error">{authError}</div>}
            <button className="auth-button" type="submit" disabled={loadingAuth}>
              {loadingAuth
                ? authMode === 'login'
                  ? 'Signing in…'
                  : 'Creating account…'
                : authMode === 'login'
                  ? 'Sign in'
                  : 'Create Account'}
            </button>
          </form>
          <div className="auth-toggle">
            {authMode === 'login' ? (
              <>
                <span>Don&apos;t have an account?</span>
                <button
                  type="button"
                  className="auth-link"
                  onClick={() => {
                    setAuthMode('signup');
                    setAuthError('');
                  }}
                >
                  Sign up
                </button>
              </>
            ) : (
              <>
                <span>Already have an account?</span>
                <button
                  type="button"
                  className="auth-link"
                  onClick={() => {
                    setAuthMode('login');
                    setAuthError('');
                  }}
                >
                  Sign in
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (showProfile) {
    const firstLetter = currentUser?.username?.[0]?.toUpperCase();
    return (
      <div className="app-root app-root--auth">
        <div className="auth-card profile-card">
          <div className="auth-title">Edit Profile</div>
          <div className="auth-subtitle">Update your avatar and account</div>

          <div className="profile-avatar-wrapper">
            {currentUser?.profile_pic_url ? (
              <img
                src={currentUser.profile_pic_url}
                alt={currentUser.username}
                className="profile-avatar profile-avatar-image"
              />
            ) : (
              <div className="profile-avatar profile-avatar-placeholder">{firstLetter}</div>
            )}
          </div>

          <div className="profile-actions">
            <label className="profile-upload-btn">
              <input
                type="file"
                accept="image/*"
                onChange={handleProfilePicChange}
                disabled={updatingProfile}
              />
              {updatingProfile ? 'Updating…' : 'Change profile photo'}
            </label>
            {profileError && <div className="profile-error">{profileError}</div>}
          </div>

          <div className="profile-footer">
            <button
              type="button"
              className="profile-back-link"
              onClick={() => setShowProfile(false)}
            >
              ← Back to chat
            </button>
            <button
              type="button"
              className="profile-logout-btn"
              onClick={handleLogout}
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-root">
      {/* Toasts (in-app popups) */}
      <div className="toast-container" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className="toast" role="status" onClick={() => openFromToast(t.userId, t.id, t.chatId)}>
            <div className="toast-title">{t.title}</div>
            {t.body && <div className="toast-body">{t.body}</div>}
          </div>
        ))}
      </div>
      <div
        className={
          `chat-shell${!activeChat ? ' chat-shell--mobile-list-only' : ''}`
        }
      >
        <aside className="sidebar">
          <div className="sidebar-header">
            <div className="user-header">
              <div className="user-header-avatar-wrapper">
                {currentUser?.profile_pic_url ? (
                  <img
                    src={currentUser.profile_pic_url}
                    alt={currentUser.username}
                    className="user-header-avatar"
                  />
                ) : (
                  <div className="user-header-avatar user-header-avatar--placeholder">
                    {currentUser?.username?.[0]?.toUpperCase()}
                  </div>
                )}
              </div>
              <div className="user-header-name-row">
                <span className="user-status-dot" />
                <span className="user-header-name">{currentUser?.username}</span>
              </div>
            </div>
            <button
              type="button"
              className="edit-profile-btn"
              onClick={() => setShowProfile(true)}
            >
              Edit
            </button>
            <button type="button" className="logout-btn" onClick={handleLogout} title="Logout">
              ⏻
            </button>
          </div>

          {/* Tab Switcher */}
          <div className="chat-tabs">
            <button
              type="button"
              className={`chat-tab ${chatTab === 'private' ? 'chat-tab--active' : ''}`}
              onClick={() => setChatTab('private')}
            >
              Private
            </button>
            <button
              type="button"
              className={`chat-tab ${chatTab === 'groups' ? 'chat-tab--active' : ''}`}
              onClick={() => setChatTab('groups')}
            >
              Groups
            </button>
          </div>

          {/* Private Chats */}
          {chatTab === 'private' && (
            <div className="sidebar-section">
              <div className="sidebar-search">
                <input
                  type="text"
                  className="sidebar-search-input"
                  placeholder="Search people"
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                />
              </div>
              <div className="sidebar-list">
                {filteredUsers.map((u) => (
                  <button
                    key={u.id}
                    type="button"
                    className={
                      activeChat?.type === 'direct' && activeChat?.raw?.id === u.id
                        ? 'sidebar-item sidebar-item--active'
                        : 'sidebar-item'
                    }
                    onClick={() => openDirectChat(u)}
                  >
                    {u.profile_pic_url ? (
                      <img
                        src={u.profile_pic_url}
                        alt={u.username}
                        className="sidebar-item-avatar sidebar-item-avatar-image"
                      />
                    ) : (
                      <div className="sidebar-item-avatar">
                        {u.username[0]?.toUpperCase()}
                      </div>
                    )}
                    <div className="sidebar-item-body">
                      <div className="sidebar-item-row">
                        <span className="sidebar-item-name">{u.username}</span>
                        {unreadCounts[`user_${u.id}`] > 0 && (
                          <div className="sidebar-unread-badge">{unreadCounts[`user_${u.id}`]}</div>
                        )}
                        <span className="sidebar-item-status online" />
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Group Chats */}
          {chatTab === 'groups' && (
            <div className="sidebar-section">
              <div className="sidebar-section-header">
                <button
                  type="button"
                  className="create-group-btn"
                  onClick={() => setShowCreateGroup(true)}
                  title="Create new group"
                >
                  + New Group
                </button>
              </div>
              <div className="sidebar-list">
                {sortedGroups.map((g) => (
                  <button
                    key={g.id}
                    type="button"
                    className={
                      activeChat?.type === 'group' && activeChat?.id === g.id
                        ? 'sidebar-item sidebar-item--active'
                        : 'sidebar-item'
                    }
                    onClick={() => openGroupChat(g)}
                  >
                    <div className="sidebar-item-avatar sidebar-item-avatar--group">#</div>
                    <div className="sidebar-item-body">
                      <div className="sidebar-item-row">
                        <span className="sidebar-item-name">{g.name}</span>
                        {unreadCounts[`group_${g.id}`] > 0 && (
                          <div className="sidebar-unread-badge">{unreadCounts[`group_${g.id}`]}</div>
                        )}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </aside>

        {/* Create Group Modal */}
        {showCreateGroup && (
          <div className="modal-overlay" onClick={() => setShowCreateGroup(false)}>
            <div className="modal-content modal-content--large" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">Create New Group</div>
              <input
                type="text"
                className="modal-input"
                placeholder="Group name"
                value={newGroupName}
                onChange={(e) => setNewGroupName(e.target.value)}
                autoFocus
              />
              
              <div className="modal-section-title">Add Members</div>
              <div className="member-selection-list">
                {filteredUsers.map((u) => (
                  <label key={u.id} className="member-selection-item">
                    <input
                      type="checkbox"
                      checked={selectedMembers.includes(u.id)}
                      onChange={() => toggleMemberSelection(u.id)}
                    />
                    <span className="member-avatar">{u.username[0]?.toUpperCase()}</span>
                    <span className="member-name">{u.username}</span>
                  </label>
                ))}
              </div>
              {selectedMembers.length > 0 && (
                <div className="selected-count">
                  {selectedMembers.length} member{selectedMembers.length > 1 ? 's' : ''} selected
                </div>
              )}
              
              <div className="modal-actions">
                <button
                  type="button"
                  className="modal-btn modal-btn--cancel"
                  onClick={() => {
                    setShowCreateGroup(false);
                    setNewGroupName('');
                    setSelectedMembers([]);
                  }}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="modal-btn modal-btn--confirm"
                  onClick={handleCreateGroup}
                  disabled={!newGroupName.trim()}
                >
                  Create
                </button>
              </div>
            </div>
          </div>
        )}

        <section
          className={
            `chat-pane${!activeChat ? ' chat-pane--hidden-mobile' : ''}`
          }
        >
          <header className="chat-header">
            {activeChat && (
              <div className="chat-header-avatar">
                {activeChat.type === 'group' ? '#' : activeChat.name[0]?.toUpperCase()}
              </div>
            )}
            <div className="chat-header-main">
              <div className="chat-title">
                {activeChat ? activeChat.name : 'Select a chat'}
              </div>
              <div className="chat-subtitle">
                {connecting
                  ? 'connecting…'
                  : activeChat
                    ? 'online'
                    : 'Select a chat'}
              </div>
            </div>
            <div className="chat-header-actions">
              <button type="button" className="icon-button" aria-label="Video call">
                📹
              </button>
              <button type="button" className="icon-button" aria-label="Voice call">
                📞
              </button>
              <button type="button" className="icon-button" aria-label="More">
                ⋮
              </button>
            </div>
          </header>

          <div className="chat-body">
            {activeChat && (
              <div className="message-scroller">
                {messages.map((m) => {
                  // Determine ownership: normalize both IDs to numbers for safe comparison
                  const msgSenderId = m.sender_id != null ? Number(m.sender_id) : null;
                  const myId = currentUser?.id != null ? Number(currentUser.id) : null;
                  const isOwn = msgSenderId !== null && myId !== null && msgSenderId === myId;
                  const time = m.created_at
                    ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    : '';
                  return (
                    <div
                      key={m.id}
                      className={isOwn ? 'message-row message-row--own' : 'message-row'}
                    >
                      <div
                        className={
                          isOwn
                            ? 'message-bubble message-bubble--own'
                            : 'message-bubble'
                        }
                      >
                        {!isOwn && m.sender && activeChat.type === 'group' && (
                          <div className="message-sender">{m.sender}</div>
                        )}
                        <div className="message-content">
                          <span className="message-text">{m.text}</span>
                          <span className="message-meta">
                            <span className="message-time">{time}</span>
                            {isOwn && <span className="message-ticks">✓✓</span>}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
          {activeChat && (
            <footer className="chat-composer">
              <div className="composer-shell">
                <input
                  type="text"
                  className="composer-input"
                  placeholder="Type a message…"
                  disabled={!activeChat}
                  value={composerText}
                  onChange={(e) => {
                    setComposerText(e.target.value);
                    setIsTyping(!!e.target.value);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                />
                <button
                  type="button"
                  className="composer-send"
                  onClick={handleSend}
                  disabled={!activeChat || !composerText.trim()}
                  aria-label="Send"
                >
                  ➤
                </button>
              </div>
            </footer>
          )}
        </section>
      </div>
    </div>
  );
}

export default App;
