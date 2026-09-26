import React, { useState, useEffect } from 'react';
import './App.css';
import { 
  Plus, 
  Layers, 
  ClipboardList, 
  Headset, 
  PieChart, 
  Users, 
  Clock, 
  CheckCircle, 
  AlertCircle, 
  MessageSquare, 
  FileText, 
  Search, 
  Lock, 
  X,
  Award,
  Calendar,
  DollarSign,
  Laptop,
  UserPlus
} from 'lucide-react';

const API_BASE = "http://127.0.0.1:8000/api";

export default function App() {
  // 1. Current Demo User State
  const [currentUser, setCurrentUser] = useState({
    id: "u1",
    username: "john.doe",
    full_name: "John Doe",
    role: "employee",
    department: "Engineering"
  });

  // 2. Active View Tab
  const [currentTab, setCurrentTab] = useState("requests");

  // 3. Data States
  const [requests, setRequests] = useState([]);
  const [categories, setCategories] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [allUsers, setAllUsers] = useState([]);

  // 4. Modal States
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState(null);

  // 5. Filter & Search State
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  // 6. Form State for Creating Requests
  const [formData, setFormData] = useState({
    category_id: "leave_clarification",
    title: "",
    description: "",
    priority: "medium",
    custom_data: {}
  });

  // 7. Comment Form State
  const [newComment, setNewComment] = useState("");
  const [isInternalNote, setIsInternalNote] = useState(false);

  // Demo User Directory for 1-Click Switcher
  const demoUsers = [
    { id: "u1", username: "john.doe", full_name: "John Doe", role: "employee", department: "Engineering" },
    { id: "u2", username: "sarah.smith", full_name: "Sarah Smith", role: "employee", department: "Marketing" },
    { id: "u3", username: "elena.hr", full_name: "Elena Rostova", role: "hr", department: "Human Resources" },
    { id: "u4", username: "david.payroll", full_name: "David Miller", role: "payroll", department: "Finance & Payroll" },
    { id: "u5", username: "alex.it", full_name: "Alex Rivera", role: "it", department: "IT Operations" },
    { id: "u6", username: "admin", full_name: "Admin Marcus", role: "admin", department: "Executive Ops" }
  ];

  // Fetch initial data
  useEffect(() => {
    fetchCategories();
    fetchUsers();
  }, []);

  useEffect(() => {
    fetchRequests();
    if (currentTab === "analytics") {
      fetchAnalytics();
    }
  }, [currentUser, currentTab]);

  const fetchCategories = async () => {
    try {
      const res = await fetch(`${API_BASE}/categories`);
      if (res.ok) {
        const data = await res.json();
        setCategories(data);
        if (data.length > 0) {
          setFormData(prev => ({ 
            ...prev, 
            category_id: prev.category_id && data.some(d => d.id === prev.category_id) ? prev.category_id : data[0].id 
          }));
        }
      }
    } catch (err) {
      console.error("Failed to load categories", err);
    }
  };

  const fetchUsers = async () => {
    try {
      const res = await fetch(`${API_BASE}/users`);
      if (res.ok) {
        const data = await res.json();
        setAllUsers(data);
      }
    } catch (err) {
      console.error("Failed to load users", err);
    }
  };

  const fetchRequests = async () => {
    try {
      let url = `${API_BASE}/requests?user_id=${currentUser.id}&role=${currentUser.role}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setRequests(data);
      }
    } catch (err) {
      console.error("Failed to load requests", err);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const res = await fetch(`${API_BASE}/analytics`);
      if (res.ok) {
        const data = await res.json();
        setAnalytics(data);
      }
    } catch (err) {
      console.error("Failed to load analytics", err);
    }
  };

  const openRequestDetail = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/requests/${id}?role=${currentUser.role}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedRequest(data);
      }
    } catch (err) {
      console.error("Failed to fetch request detail", err);
    }
  };

  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        user_id: currentUser.id,
        category_id: formData.category_id,
        title: formData.title,
        description: formData.description,
        priority: formData.priority,
        custom_data: formData.custom_data
      };

      const res = await fetch(`${API_BASE}/requests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        setShowCreateModal(false);
        setFormData({
          category_id: "leave",
          title: "",
          description: "",
          priority: "medium",
          custom_data: {}
        });
        fetchRequests();
      }
    } catch (err) {
      console.error("Failed to create request", err);
    }
  };

  const handleStatusChange = async (newStatus) => {
    if (!selectedRequest) return;
    try {
      const res = await fetch(`${API_BASE}/requests/${selectedRequest.id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus, notes: "Status updated via HR Portal" })
      });
      if (res.ok) {
        openRequestDetail(selectedRequest.id);
        fetchRequests();
      }
    } catch (err) {
      console.error("Failed to update status", err);
    }
  };

  const handleAssign = async (staffId) => {
    if (!selectedRequest) return;
    try {
      const res = await fetch(`${API_BASE}/requests/${selectedRequest.id}/assign`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assigned_to: staffId })
      });
      if (res.ok) {
        openRequestDetail(selectedRequest.id);
        fetchRequests();
      }
    } catch (err) {
      console.error("Failed to assign request", err);
    }
  };

  const handleAddComment = async (e) => {
    e.preventDefault();
    if (!newComment.trim() || !selectedRequest) return;

    try {
      const res = await fetch(`${API_BASE}/requests/${selectedRequest.id}/comments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: currentUser.id,
          user_name: currentUser.full_name,
          user_role: currentUser.role,
          message: newComment,
          is_internal: isInternalNote
        })
      });

      if (res.ok) {
        setNewComment("");
        setIsInternalNote(false);
        openRequestDetail(selectedRequest.id);
      }
    } catch (err) {
      console.error("Failed to add comment", err);
    }
  };

  // Filter requests
  const filteredRequests = requests.filter(req => {
    const matchesSearch = req.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          req.request_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          (req.requester_name && req.requester_name.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesStatus = statusFilter === "all" || req.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const activeCategory = categories.find(c => c.id === formData.category_id);

  const getCategoryIcon = (iconName) => {
    switch (iconName) {
      case 'calendar': return <Calendar size={18} />;
      case 'dollar-sign': return <DollarSign size={18} />;
      case 'award': return <Award size={18} />;
      case 'laptop': return <Laptop size={18} />;
      case 'user-plus': return <UserPlus size={18} />;
      default: return <FileText size={18} />;
    }
  };

  return (
    <div className="app-container">
      {/* 1. TOP NAVBAR */}
      <header className="navbar">
        <div className="nav-brand">
          <div className="brand-icon">
            <Layers size={22} />
          </div>
          <div className="brand-title">
            Nexus<span>HR</span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="nav-links">
          <button 
            className={`nav-btn ${currentTab === "requests" ? "active" : ""}`}
            onClick={() => setCurrentTab("requests")}
          >
            <ClipboardList size={16} />
            <span>{currentUser.role === 'employee' ? 'My Requests' : 'All Requests'}</span>
          </button>

          {currentUser.role !== 'employee' && (
            <button 
              className={`nav-btn ${currentTab === "analytics" ? "active" : ""}`}
              onClick={() => setCurrentTab("analytics")}
            >
              <PieChart size={16} />
              <span>Analytics</span>
            </button>
          )}

          {currentUser.role === 'admin' && (
            <button 
              className={`nav-btn ${currentTab === "users" ? "active" : ""}`}
              onClick={() => setCurrentTab("users")}
            >
              <Users size={16} />
              <span>Employee Directory</span>
            </button>
          )}
        </div>

        {/* User / Role Switcher */}
        <div className="nav-user-bar">
          <div className="user-selector">
            <label>Switch Demo Role:</label>
            <select 
              value={currentUser.id}
              onChange={(e) => {
                const user = demoUsers.find(u => u.id === e.target.value);
                if (user) setCurrentUser(user);
              }}
            >
              {demoUsers.map(u => (
                <option key={u.id} value={u.id}>
                  {u.full_name} ({u.role.toUpperCase()})
                </option>
              ))}
            </select>
          </div>

          <div className="user-badge">
            <div className="avatar">
              {currentUser.full_name.charAt(0)}
            </div>
            <div className="user-info">
              <span className="user-name">{currentUser.full_name}</span>
              <span className="user-role-tag">{currentUser.role} • {currentUser.department}</span>
            </div>
          </div>
        </div>
      </header>

      {/* 2. MAIN CONTENT AREA */}
      <main className="main-content">
        {/* VIEW A: REQUESTS LIST */}
        {currentTab === "requests" && (
          <div>
            <div className="view-header">
              <div>
                <h1 className="view-title">
                  {currentUser.role === 'employee' ? 'My Service Requests' : 'HR Service Desk'}
                </h1>
                <p className="view-subtitle">
                  {currentUser.role === 'employee' 
                    ? 'Track and manage your submitted HR tickets, inquiries, and certificates.'
                    : `Managing queue as ${currentUser.role.toUpperCase()} specialist.`}
                </p>
              </div>

              {currentUser.role === 'employee' && (
                <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
                  <Plus size={18} />
                  <span>Raise Request</span>
                </button>
              )}
            </div>

            {/* Filter Bar */}
            <div className="filter-bar">
              <input 
                type="text" 
                className="search-input" 
                placeholder="Search requests by title, ticket #, or employee..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />

              <select 
                className="filter-select"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="all">All Statuses</option>
                <option value="submitted">Submitted</option>
                <option value="in_progress">In Progress</option>
                <option value="resolved">Resolved</option>
                <option value="closed">Closed</option>
              </select>
            </div>

            {/* Request Cards Grid */}
            <div className="requests-grid">
              {filteredRequests.map(req => (
                <div 
                  key={req.id} 
                  className="request-card"
                  onClick={() => openRequestDetail(req.id)}
                >
                  <div>
                    <div className="card-header">
                      <span className="req-number">{req.request_number}</span>
                      <span className={`priority-badge priority-${req.priority}`}>
                        {req.priority}
                      </span>
                    </div>

                    <h3 className="card-title">{req.title}</h3>
                    <p className="card-desc">{req.description}</p>
                  </div>

                  <div className="card-footer">
                    <div className="requester-info">
                      <span className="requester-name">{req.requester_name || "Employee"}</span>
                      <span className="requester-dept">{req.category_name}</span>
                    </div>

                    <span className={`badge badge-${req.status}`}>
                      {req.status.replace('_', ' ')}
                    </span>
                  </div>
                </div>
              ))}

              {filteredRequests.length === 0 && (
                <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                  No requests found matching your filter criteria.
                </div>
              )}
            </div>
          </div>
        )}

        {/* VIEW B: ANALYTICS DASHBOARD */}
        {currentTab === "analytics" && analytics && (
          <div>
            <div className="view-header">
              <div>
                <h1 className="view-title">HR Operations Analytics</h1>
                <p className="view-subtitle">Real-time resolution metrics, ticket distribution, and backlog status.</p>
              </div>
            </div>

            {/* KPI Cards */}
            <div className="kpi-grid">
              <div className="kpi-card">
                <div className="kpi-title">Total Requests</div>
                <div className="kpi-val" style={{ color: '#818CF8' }}>{analytics.total}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-title">In Progress</div>
                <div className="kpi-val" style={{ color: '#FBBF24' }}>{analytics.status_counts.in_progress || 0}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-title">Resolved Tickets</div>
                <div className="kpi-val" style={{ color: '#34D399' }}>{analytics.status_counts.resolved || 0}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-title">Avg SLA Resolution</div>
                <div className="kpi-val" style={{ color: '#60A5FA' }}>18.4 hrs</div>
              </div>
            </div>

            {/* Category Breakdown Table */}
            <div className="kpi-card" style={{ marginTop: '24px' }}>
              <h3 style={{ marginBottom: '16px', fontSize: '18px' }}>Requests by HR Category</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
                {Object.entries(analytics.category_counts).map(([cat, count]) => (
                  <div key={cat} style={{ background: 'var(--bg-input)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>{cat}</div>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', marginTop: '4px' }}>{count}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* VIEW C: ADMIN DIRECTORY */}
        {currentTab === "users" && (
          <div>
            <div className="view-header">
              <div>
                <h1 className="view-title">Employee & Staff Directory</h1>
                <p className="view-subtitle">System-wide directory of employees, HR managers, and administrators.</p>
              </div>
            </div>

            <div className="requests-grid">
              {allUsers.map(u => (
                <div key={u.id} className="request-card" style={{ cursor: 'default' }}>
                  <div className="card-header">
                    <span className="req-number">{u.department || 'Corporate'}</span>
                    <span className="priority-badge priority-medium">{u.role}</span>
                  </div>
                  <h3 className="card-title">{u.full_name}</h3>
                  <p className="card-desc">Username: @{u.username} • {u.email}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* 3. CREATE REQUEST MODAL */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-card" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">Submit New Service Request</h2>
              <button className="close-btn" onClick={() => setShowCreateModal(false)}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit}>
              {/* Category Picker */}
              <div className="form-group">
                <label className="form-label">Select Request Category</label>
                <select 
                  className="form-select"
                  value={formData.category_id}
                  onChange={(e) => setFormData({ ...formData, category_id: e.target.value, custom_data: {} })}
                >
                  {categories.map(c => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>

              {/* Title */}
              <div className="form-group">
                <label className="form-label">Subject / Title</label>
                <input 
                  type="text" 
                  className="form-input" 
                  placeholder="e.g. Request for Official Experience Letter"
                  required
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                />
              </div>

              {/* Priority */}
              <div className="form-group">
                <label className="form-label">Priority Level</label>
                <select 
                  className="form-select"
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              </div>

              {/* Dynamic Category Fields */}
              {activeCategory && activeCategory.fields && activeCategory.fields.map(field => (
                <div className="form-group" key={field.name}>
                  <label className="form-label">{field.label}</label>
                  {field.type === 'select' ? (
                    <select 
                      className="form-select"
                      required
                      value={formData.custom_data[field.name] || ''}
                      onChange={(e) => setFormData({
                        ...formData,
                        custom_data: { ...formData.custom_data, [field.name]: e.target.value }
                      })}
                    >
                      <option value="">-- Choose Option --</option>
                      {field.options.map(opt => (
                        <option key={opt} value={opt}>{opt}</option>
                      ))}
                    </select>
                  ) : (
                    <input 
                      type={field.type || 'text'}
                      className="form-input"
                      required
                      value={formData.custom_data[field.name] || ''}
                      onChange={(e) => setFormData({
                        ...formData,
                        custom_data: { ...formData.custom_data, [field.name]: e.target.value }
                      })}
                    />
                  )}
                </div>
              ))}

              {/* Description */}
              <div className="form-group">
                <label className="form-label">Detailed Notes / Background</label>
                <textarea 
                  className="form-textarea" 
                  placeholder="Provide any additional relevant details..."
                  required
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
                <button type="button" className="btn-secondary" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Submit Request
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 4. REQUEST DETAIL DRAWER / MODAL */}
      {selectedRequest && (
        <div className="modal-overlay" onClick={() => setSelectedRequest(null)}>
          <div className="modal-card" style={{ maxWidth: '850px' }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <span className="req-number">{selectedRequest.request_number}</span>
                <h2 className="modal-title" style={{ marginTop: '6px' }}>{selectedRequest.title}</h2>
              </div>
              <button className="close-btn" onClick={() => setSelectedRequest(null)}>
                <X size={20} />
              </button>
            </div>

            <div className="detail-grid">
              {/* Main Column */}
              <div className="detail-main">
                <div>
                  <h4 style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '6px' }}>Description</h4>
                  <p style={{ lineHeight: 1.6, fontSize: '14px' }}>{selectedRequest.description}</p>
                </div>

                {/* Custom Data Values */}
                {Object.keys(selectedRequest.custom_data).length > 0 && (
                  <div style={{ background: 'var(--bg-input)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <h4 style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
                      Category Specific Data
                    </h4>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '13px' }}>
                      {Object.entries(selectedRequest.custom_data).map(([k, v]) => (
                        <div key={k}>
                          <span style={{ color: 'var(--text-dim)' }}>{k.replace('_', ' ')}: </span>
                          <span style={{ fontWeight: '600' }}>{v}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Experience Letter Preview if category is experience */}
                {selectedRequest.category_id === 'experience' && (
                  <div className="cert-preview">
                    <div className="cert-title">Official Certificate of Employment</div>
                    <div className="cert-body">
                      This is to certify that <strong>{selectedRequest.requester_name}</strong> is currently employed with Nexus Corporation in the <strong>{selectedRequest.requester_dept}</strong> department. 
                      This certificate is issued for <strong>{selectedRequest.custom_data.purpose || 'Official Verification'}</strong>.
                      <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'space-between' }}>
                        <div>Issued on: {new Date().toLocaleDateString()}</div>
                        <div>Authorized HR Signatory (Elena Rostova)</div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Discussion Thread */}
                <div className="comments-section">
                  <h4 style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: '12px' }}>
                    Discussion Thread ({selectedRequest.comments?.length || 0})
                  </h4>

                  <div className="comment-list">
                    {selectedRequest.comments?.map(c => (
                      <div key={c.id} className={`comment-box ${c.is_internal ? 'internal' : ''}`}>
                        <div className="comment-header">
                          <span className="comment-author">
                            {c.user_name} ({c.user_role})
                          </span>
                          {c.is_internal === 1 && (
                            <span className="comment-internal-tag">INTERNAL NOTE</span>
                          )}
                        </div>
                        <div className="comment-msg">{c.message}</div>
                      </div>
                    ))}
                    {(!selectedRequest.comments || selectedRequest.comments.length === 0) && (
                      <div style={{ fontSize: '13px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                        No messages yet in this ticket.
                      </div>
                    )}
                  </div>

                  {/* Comment Input Form */}
                  <form onSubmit={handleAddComment}>
                    <textarea 
                      className="form-textarea"
                      placeholder="Write a message to requester or HR staff..."
                      style={{ minHeight: '70px', marginBottom: '8px' }}
                      value={newComment}
                      onChange={e => setNewComment(e.target.value)}
                    />
                    
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      {currentUser.role !== 'employee' ? (
                        <label style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                          <input 
                            type="checkbox" 
                            checked={isInternalNote} 
                            onChange={e => setIsInternalNote(e.target.checked)} 
                          />
                          <span>Private Internal Note (Hidden from employee)</span>
                        </label>
                      ) : <div />}

                      <button type="submit" className="btn-primary" style={{ padding: '6px 14px', fontSize: '13px' }}>
                        Send Message
                      </button>
                    </div>
                  </form>
                </div>
              </div>

              {/* Sidebar Column */}
              <div className="detail-sidebar">
                <div>
                  <label className="form-label">Current Status</label>
                  <span className={`badge badge-${selectedRequest.status}`} style={{ width: '100%', justifyContent: 'center', padding: '6px' }}>
                    {selectedRequest.status.replace('_', ' ')}
                  </span>
                </div>

                {/* Status Updater for HR/Admin or Closure by Employee */}
                {(currentUser.role !== 'employee' || selectedRequest.status === 'resolved') && (
                  <div>
                    <label className="form-label">Update Status</label>
                    <select 
                      className="form-select"
                      value={selectedRequest.status}
                      onChange={e => handleStatusChange(e.target.value)}
                    >
                      <option value="submitted">Submitted</option>
                      <option value="in_progress">In Progress</option>
                      <option value="resolved">Resolved</option>
                      <option value="closed">Closed</option>
                    </select>
                  </div>
                )}

                {/* Assignment Picker for HR/Admin */}
                {currentUser.role !== 'employee' && (
                  <div>
                    <label className="form-label">Assigned Staff</label>
                    <select 
                      className="form-select"
                      value={selectedRequest.assigned_to || ''}
                      onChange={e => handleAssign(e.target.value)}
                    >
                      <option value="">-- Unassigned --</option>
                      {demoUsers.filter(u => u.role !== 'employee').map(s => (
                        <option key={s.id} value={s.id}>{s.full_name} ({s.role})</option>
                      ))}
                    </select>
                  </div>
                )}

                <div style={{ fontSize: '12px', color: 'var(--text-muted)', borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
                  <div><strong>Requester:</strong> {selectedRequest.requester_name}</div>
                  <div><strong>Email:</strong> {selectedRequest.requester_email}</div>
                  <div><strong>Category:</strong> {selectedRequest.category_name}</div>
                  <div><strong>Priority:</strong> {selectedRequest.priority}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
