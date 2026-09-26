/**
 * NEXUS HR SERVICE PORTAL — CORE APPLICATION CONTROLLER
 */

class NexusHRApp {
  constructor() {
    this.apiBase = '';
    this.token = localStorage.getItem('nexushr_token') || null;
    this.currentUser = JSON.parse(localStorage.getItem('nexushr_user') || 'null');
    
    this.categories = [];
    this.requests = [];
    this.staffList = [];
    this.notifications = [];
    this.activeView = 'my_requests';
    this.selectedFormCategory = 'leave_clarification';
    this.activeRequestDetail = null;
    this.activeCommentTab = 'public';
    this.searchDebounceTimer = null;
    this.hrFilterMode = 'all';

    this.init();
  }

  async init() {
    let isAuthenticated = false;
    if (this.token) {
      try {
        const res = await fetch('/api/auth/me', {
          headers: { 'Authorization': `Bearer ${this.token}` }
        });
        if (res.ok) {
          this.currentUser = await res.json();
          localStorage.setItem('nexushr_user', JSON.stringify(this.currentUser));
          this.updateUserUI();
          isAuthenticated = true;
        }
      } catch (e) {
        console.warn('Existing token validation failed, resetting...', e);
      }
    }

    if (!isAuthenticated) {
      await this.quickLogin('john.doe', 'emp123', false);
    } else {
      await this.fetchCategories();
      await this.fetchStaffList();
      await this.fetchRequests();
      await this.fetchNotifications();
    }

    // Start background poll for notifications every 30s
    setInterval(() => this.fetchNotifications(true), 30000);
  }

  /* ================= AUTHENTICATION & SESSION ================= */

  async quickLogin(username, password, showToast = true) {
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username_or_email: username, password })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Login failed');
      }

      const data = await res.json();
      this.token = data.access_token;
      this.currentUser = data.user;
      localStorage.setItem('nexushr_token', this.token);
      localStorage.setItem('nexushr_user', JSON.stringify(this.currentUser));

      this.updateUserUI();
      this.closeModal('authModal');
      
      // Reset view to appropriate default
      if (['hr', 'payroll', 'it', 'admin'].includes(this.currentUser.role)) {
        this.switchView('hr_desk');
      } else {
        this.switchView('my_requests');
      }

      await this.fetchRequests();
      await this.fetchNotifications();

      if (showToast) {
        this.showToast(`Signed in as ${this.currentUser.full_name} (${this.currentUser.role.toUpperCase()})`, 'success');
      }
    } catch (e) {
      this.showToast(e.message, 'error');
    }
  }

  async handleLoginSubmit(event) {
    event.preventDefault();
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    await this.quickLogin(username, password, true);
  }

  async handleRegisterSubmit(event) {
    event.preventDefault();
    try {
      const payload = {
        full_name: document.getElementById('regFullName').value,
        username: document.getElementById('regUsername').value,
        email: document.getElementById('regEmail').value,
        department: document.getElementById('regDepartment').value || 'General',
        designation: document.getElementById('regDesignation').value || 'Employee',
        role: document.getElementById('regRole').value,
        password: document.getElementById('regPassword').value
      };

      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Registration failed');
      }

      const data = await res.json();
      this.token = data.access_token;
      this.currentUser = data.user;
      localStorage.setItem('nexushr_token', this.token);
      localStorage.setItem('nexushr_user', JSON.stringify(this.currentUser));

      this.updateUserUI();
      this.closeModal('authModal');
      this.switchView('my_requests');
      await this.fetchRequests();
      await this.fetchNotifications();
      this.showToast(`Account created! Welcome, ${this.currentUser.full_name}`, 'success');
    } catch (e) {
      this.showToast(e.message, 'error');
    }
  }

  logout() {
    this.token = null;
    this.currentUser = null;
    localStorage.removeItem('nexushr_token');
    localStorage.removeItem('nexushr_user');
    this.closeUserMenu();
    this.quickLogin('john.doe', 'emp123', false);
    this.showToast('Signed out. Switched to demo Employee.', 'info');
  }

  updateUserUI() {
    if (!this.currentUser) return;
    
    // Header user info
    const initials = this.currentUser.full_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
    document.getElementById('userAvatar').textContent = initials;
    document.getElementById('userName').textContent = this.currentUser.full_name;
    document.getElementById('userRoleBadge').textContent = this.currentUser.role.toUpperCase();
    document.getElementById('userEmail').textContent = this.currentUser.email;
    document.getElementById('userDept').textContent = `${this.currentUser.department || 'Operations'} • ${this.currentUser.employee_id || 'EMP-XXXX'}`;
    
    const heroName = document.getElementById('heroUserName');
    if (heroName) heroName.textContent = this.currentUser.full_name.split(' ')[0];

    // Role-based visibility toggles
    const isStaff = ['hr', 'payroll', 'it', 'admin'].includes(this.currentUser.role);
    const isAdmin = this.currentUser.role === 'admin';

    document.querySelectorAll('.hr-only').forEach(el => {
      el.style.display = isStaff ? '' : 'none';
    });
    document.querySelectorAll('.admin-only').forEach(el => {
      el.style.display = isAdmin ? '' : 'none';
    });
  }

  /* ================= VIEW NAVIGATION ================= */

  switchView(viewName) {
    this.activeView = viewName;

    // Update Nav Buttons
    document.querySelectorAll('.main-nav-links .nav-item').forEach(btn => btn.classList.remove('active'));
    if (viewName === 'my_requests') document.getElementById('tabMyRequests')?.classList.add('active');
    if (viewName === 'hr_desk') document.getElementById('tabHrDesk')?.classList.add('active');
    if (viewName === 'analytics') document.getElementById('tabAnalytics')?.classList.add('active');
    if (viewName === 'admin') document.getElementById('tabAdmin')?.classList.add('active');

    // Toggle Section Panels
    document.getElementById('viewMyRequests').style.display = viewName === 'my_requests' ? 'block' : 'none';
    document.getElementById('viewHrDesk').style.display = viewName === 'hr_desk' ? 'block' : 'none';
    document.getElementById('viewAnalytics').style.display = viewName === 'analytics' ? 'block' : 'none';
    document.getElementById('viewAdmin').style.display = viewName === 'admin' ? 'block' : 'none';

    // Trigger specific view loaders
    if (viewName === 'my_requests' || viewName === 'hr_desk') {
      this.fetchRequests();
    } else if (viewName === 'analytics') {
      this.fetchAnalytics();
    } else if (viewName === 'admin') {
      this.fetchAdminUsers();
    }
  }

  /* ================= DATA FETCHING ================= */

  async fetchCategories() {
    try {
      const res = await fetch('/api/categories', {
        headers: { 'Authorization': `Bearer ${this.token}` }
      });
      if (res.ok) {
        this.categories = await res.json();
      }
    } catch (e) {
      console.error('Error fetching categories:', e);
    }
  }

  async fetchStaffList() {
    try {
      const res = await fetch('/api/auth/staff', {
        headers: { 'Authorization': `Bearer ${this.token}` }
      });
      if (res.ok) {
        this.staffList = await res.json();
        this.populateStaffDropdown();
      }
    } catch (e) {
      console.error('Error fetching staff list:', e);
    }
  }

  populateStaffDropdown() {
    const select = document.getElementById('actionAssignSelect');
    if (!select) return;
    select.innerHTML = '<option value="">-- Unassigned --</option>';
    this.staffList.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s.id;
      opt.textContent = `${s.full_name} (${s.role.toUpperCase()} - ${s.department})`;
      select.appendChild(opt);
    });
  }

  async fetchRequests() {
    const isDesk = this.activeView === 'hr_desk';
    const catFilter = document.getElementById('reqCategoryFilter')?.value || '';
    const statusFilter = document.getElementById('reqStatusFilter')?.value || '';
    const priorityFilter = document.getElementById('reqPriorityFilter')?.value || '';
    const search = document.getElementById('reqSearchInput')?.value || '';

    let url = `/api/requests?`;
    if (catFilter) url += `category_id=${catFilter}&`;
    if (statusFilter) url += `status=${statusFilter}&`;
    if (priorityFilter) url += `priority=${priorityFilter}&`;
    if (search) url += `search=${encodeURIComponent(search)}&`;

    if (isDesk && this.hrFilterMode === 'my') {
      url += `my_assigned_only=true&`;
    }

    try {
      const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${this.token}` }
      });
      if (!res.ok) throw new Error('Failed to fetch requests');
      
      let data = await res.json();

      if (isDesk && this.hrFilterMode === 'unassigned') {
        data = data.filter(r => !r.assigned_to);
      } else if (isDesk && this.hrFilterMode === 'overdue') {
        data = data.filter(r => r.is_overdue);
      }

      this.requests = data;
      this.renderRequestsList();
      this.updateKPIs(data);
    } catch (e) {
      console.error(e);
      this.showToast('Error loading requests', 'error');
    }
  }

  updateKPIs(requests) {
    const total = requests.length;
    const pending = requests.filter(r => ['submitted', 'under_review'].includes(r.status)).length;
    const progress = requests.filter(r => ['in_progress', 'on_hold'].includes(r.status)).length;
    const resolved = requests.filter(r => ['resolved', 'closed'].includes(r.status)).length;

    document.getElementById('kpiTotalReqs').textContent = total;
    document.getElementById('kpiPendingReqs').textContent = pending;
    document.getElementById('kpiProgressReqs').textContent = progress;
    document.getElementById('kpiResolvedReqs').textContent = resolved;

    // HR badge in navbar
    const pendingCount = requests.filter(r => r.status === 'submitted' || r.is_overdue).length;
    const badge = document.getElementById('hrPendingBadge');
    if (badge) {
      badge.textContent = pendingCount;
      badge.style.display = pendingCount > 0 ? 'inline-block' : 'none';
    }
  }

  renderRequestsList() {
    if (this.activeView === 'my_requests') {
      this.renderEmployeeCards();
    } else if (this.activeView === 'hr_desk') {
      this.renderHrDeskTable();
    }
  }

  renderEmployeeCards() {
    const container = document.getElementById('requestsGrid');
    if (!container) return;

    if (this.requests.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <i class="fa-regular fa-folder-open"></i>
          <h3>No Service Requests Found</h3>
          <p class="text-muted mt-1">You haven't raised any requests matching the selected filter.</p>
          <button class="btn-primary mt-3" onclick="app.openNewRequestModal()">
            <i class="fa-solid fa-plus"></i> Raise New Request
          </button>
        </div>
      `;
      return;
    }

    container.innerHTML = this.requests.map(r => {
      const formattedDate = new Date(r.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
      return `
        <div class="request-card glass-panel" onclick="app.openRequestDetailModal(${r.id})">
          <div>
            <div class="request-card-header">
              <span class="req-cat-pill">
                <i class="fa-solid fa-${this.getCategoryIcon(r.category_id)}"></i>
                ${r.category_name}
              </span>
              <span class="req-number-badge">${r.request_number}</span>
            </div>
            <h3 class="request-card-title">${this.escapeHTML(r.title)}</h3>
            <p class="request-card-desc">${this.escapeHTML(r.description)}</p>
          </div>

          <div class="request-card-footer">
            <div class="req-badges-row">
              <span class="status-badge status-${r.status}">
                ${this.getStatusLabel(r.status)}
              </span>
              <span class="priority-badge priority-${r.priority}">
                ${r.priority}
              </span>
              ${r.is_confidential ? `<span class="confidential-badge"><i class="fa-solid fa-lock"></i> Confidential</span>` : ''}
              ${r.is_overdue ? `<span class="overdue-pill"><i class="fa-solid fa-triangle-exclamation"></i> Overdue</span>` : ''}
            </div>
            <div class="req-meta-right">
              ${r.comment_count > 0 ? `<span><i class="fa-regular fa-comment"></i> ${r.comment_count}</span>` : ''}
              ${r.attachment_count > 0 ? `<span><i class="fa-solid fa-paperclip"></i> ${r.attachment_count}</span>` : ''}
              <span>${formattedDate}</span>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  renderHrDeskTable() {
    const tbody = document.getElementById('hrDeskTableBody');
    if (!tbody) return;

    if (this.requests.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" class="text-center py-4 text-muted">No tickets found for the active criteria.</td></tr>`;
      return;
    }

    tbody.innerHTML = this.requests.map(r => {
      const createdTime = new Date(r.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
      return `
        <tr onclick="app.openRequestDetailModal(${r.id})" style="cursor: pointer;">
          <td class="font-bold text-indigo">${r.request_number}</td>
          <td>
            <span class="req-cat-pill">
              <i class="fa-solid fa-${this.getCategoryIcon(r.category_id)}"></i>
              ${r.category_name}
            </span>
          </td>
          <td>
            <div class="requester-name font-bold">${this.escapeHTML(r.requester_name)}</div>
            <div class="text-xs text-muted">${r.requester_department || 'Staff'} • ${r.requester_employee_id || ''}</div>
          </td>
          <td>
            <div class="font-bold">${this.escapeHTML(r.title)}</div>
            ${r.is_confidential ? `<span class="confidential-badge mt-1"><i class="fa-solid fa-lock"></i> Confidential Payroll</span>` : ''}
          </td>
          <td><span class="priority-badge priority-${r.priority}">${r.priority}</span></td>
          <td><span class="status-badge status-${r.status}">${this.getStatusLabel(r.status)}</span></td>
          <td>${r.assignee_name ? `<span class="font-bold text-info">${this.escapeHTML(r.assignee_name)}</span>` : `<span class="text-muted italic">Unassigned</span>`}</td>
          <td>
            ${r.is_overdue ? `<span class="overdue-pill"><i class="fa-solid fa-circle-exclamation"></i> Breached SLA</span>` : `<span class="text-muted">${createdTime}</span>`}
          </td>
          <td class="text-right">
            <button class="btn-secondary btn-sm" onclick="event.stopPropagation(); app.openRequestDetailModal(${r.id})">
              Manage <i class="fa-solid fa-arrow-right"></i>
            </button>
          </td>
        </tr>
      `;
    }).join('');
  }

  filterHrDesk(mode) {
    this.hrFilterMode = mode;
    document.querySelectorAll('.desk-quick-filters .filter-tab').forEach(b => b.classList.remove('active'));
    event?.target?.classList.add('active');
    this.fetchRequests();
  }

  filterByStatus(status) {
    const select = document.getElementById('reqStatusFilter');
    if (select) {
      select.value = status;
      this.fetchRequests();
    }
  }

  resetFilters() {
    if (document.getElementById('reqSearchInput')) document.getElementById('reqSearchInput').value = '';
    if (document.getElementById('reqCategoryFilter')) document.getElementById('reqCategoryFilter').value = '';
    if (document.getElementById('reqStatusFilter')) document.getElementById('reqStatusFilter').value = '';
    if (document.getElementById('reqPriorityFilter')) document.getElementById('reqPriorityFilter').value = '';
    this.fetchRequests();
  }

  debounceSearch() {
    clearTimeout(this.searchDebounceTimer);
    this.searchDebounceTimer = setTimeout(() => {
      this.fetchRequests();
    }, 300);
  }

  /* ================= REQUEST CREATION WIZARD ================= */

  openNewRequestModal() {
    this.selectedFormCategory = 'leave_clarification';
    this.renderCategoryCards();
    this.renderDynamicFields();
    document.getElementById('newRequestForm').reset();
    document.getElementById('fileNamePreview').textContent = 'No file selected';
    this.openModal('newRequestModal');
  }

  selectFormCategory(categoryId) {
    this.selectedFormCategory = categoryId;
    this.renderCategoryCards();
    this.renderDynamicFields();
  }

  renderCategoryCards() {
    document.querySelectorAll('.cat-select-card').forEach(card => {
      if (card.dataset.cat === this.selectedFormCategory) {
        card.classList.add('active');
      } else {
        card.classList.remove('active');
      }
    });
  }

  renderDynamicFields() {
    const container = document.getElementById('dynamicCategoryFields');
    if (!container) return;

    const catObj = this.categories.find(c => c.id === this.selectedFormCategory);
    if (!catObj || !catObj.fields_schema || catObj.fields_schema.length === 0) {
      container.innerHTML = '';
      container.style.display = 'none';
      return;
    }

    container.style.display = 'block';
    container.innerHTML = `
      <h4 class="sub-panel-title mb-2 text-indigo">
        <i class="fa-solid fa-list-check"></i> ${catObj.name} Specific Details
      </h4>
      <div class="form-row" style="flex-wrap: wrap;">
        ${catObj.fields_schema.map(f => {
          if (f.type === 'select') {
            return `
              <div class="form-group col-6">
                <label class="form-label">${f.label} ${f.required ? '<span class="required">*</span>' : ''}</label>
                <select class="form-control dynamic-field-input" data-field-name="${f.name}" ${f.required ? 'required' : ''}>
                  ${f.options.map(opt => `<option value="${opt}">${opt}</option>`).join('')}
                </select>
              </div>
            `;
          } else if (f.type === 'date') {
            return `
              <div class="form-group col-6">
                <label class="form-label">${f.label} ${f.required ? '<span class="required">*</span>' : ''}</label>
                <input type="date" class="form-control dynamic-field-input" data-field-name="${f.name}" ${f.required ? 'required' : ''} />
              </div>
            `;
          } else {
            return `
              <div class="form-group col-6">
                <label class="form-label">${f.label} ${f.required ? '<span class="required">*</span>' : ''}</label>
                <input type="text" class="form-control dynamic-field-input" data-field-name="${f.name}" placeholder="${f.placeholder || ''}" ${f.required ? 'required' : ''} />
              </div>
            `;
          }
        }).join('')}
      </div>
    `;
  }

  handleFileSelected(event) {
    const file = event.target.files[0];
    const preview = document.getElementById('fileNamePreview');
    if (file) {
      preview.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      preview.style.color = '#10b981';
    } else {
      preview.textContent = 'No file selected';
      preview.style.color = '';
    }
  }

  async handleCreateRequest(event) {
    event.preventDefault();
    const btn = document.getElementById('btnSubmitNewRequest');
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Submitting...';

    try {
      // Gather custom dynamic fields
      const customData = {};
      document.querySelectorAll('.dynamic-field-input').forEach(input => {
        const key = input.dataset.fieldName;
        if (key) customData[key] = input.value;
      });

      const payload = {
        category_id: this.selectedFormCategory,
        title: document.getElementById('reqTitle').value,
        description: document.getElementById('reqDescription').value,
        priority: document.getElementById('reqPriority').value,
        custom_data: customData,
        is_confidential: this.selectedFormCategory === 'payroll_query'
      };

      const res = await fetch('/api/requests', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.token}`
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to create request');
      }

      const created = await res.json();

      // If file was attached, upload it
      const fileInput = document.getElementById('reqAttachmentFile');
      if (fileInput.files && fileInput.files[0]) {
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('attachment_type', 'supporting');

        await fetch(`/api/requests/${created.id}/attachments`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${this.token}` },
          body: formData
        });
      }

      this.closeModal('newRequestModal');
      this.showToast(`Request ${created.request_number} submitted successfully!`, 'success');
      await this.fetchRequests();
      await this.fetchNotifications();
    } catch (e) {
      this.showToast(e.message, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Submit Request';
    }
  }

  /* ================= REQUEST DETAIL VIEW & WORKFLOW ================= */

  async openRequestDetailModal(requestId) {
    try {
      const res = await fetch(`/api/requests/${requestId}`, {
        headers: { 'Authorization': `Bearer ${this.token}` }
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Access denied or request not found');
      }

      const data = await res.json();
      this.activeRequestDetail = data;
      this.renderRequestDetailView();
      this.openModal('requestDetailModal');
    } catch (e) {
      this.showToast(e.message, 'error');
    }
  }

  renderRequestDetailView() {
    const r = this.activeRequestDetail;
    if (!r) return;

    // Header info
    document.getElementById('detailTicketCode').textContent = r.request_number;
    document.getElementById('detailTitle').textContent = r.title;
    document.getElementById('detailDescription').textContent = r.description;
    
    // Icon & Pill
    document.getElementById('detailCatIcon').innerHTML = `<i class="fa-solid fa-${this.getCategoryIcon(r.category_id)}"></i>`;
    
    // Badges
    const statusBadge = document.getElementById('detailStatusBadge');
    statusBadge.className = `status-badge status-${r.status}`;
    statusBadge.textContent = this.getStatusLabel(r.status);

    const prioBadge = document.getElementById('detailPriorityBadge');
    prioBadge.className = `priority-badge priority-${r.priority}`;
    prioBadge.textContent = r.priority.toUpperCase();

    const confBadge = document.getElementById('detailConfidentialBadge');
    confBadge.style.display = r.is_confidential ? 'inline-flex' : 'none';

    // Stepper nodes
    this.updateStepperProgress(r.status);

    // Resolution / Rejection Banner
    const resBox = document.getElementById('detailResolutionBox');
    if (r.status === 'rejected') {
      resBox.style.display = 'block';
      resBox.className = 'resolution-alert-box glass-panel mt-3 p-3 bg-danger-subtle';
      resBox.innerHTML = `
        <h4 class="text-danger font-bold"><i class="fa-solid fa-circle-xmark"></i> Request Rejected by HR</h4>
        <p class="text-sm mt-1"><strong>Reason:</strong> ${this.escapeHTML(r.rejection_reason || 'Does not meet current company policy criteria.')}</p>
      `;
    } else if (r.status === 'resolved' || r.status === 'closed') {
      resBox.style.display = 'block';
      resBox.className = 'resolution-alert-box glass-panel mt-3 p-3 bg-success-subtle';
      resBox.innerHTML = `
        <h4 class="text-emerald font-bold"><i class="fa-solid fa-circle-check"></i> Request Resolved by HR</h4>
        <p class="text-sm mt-1">${this.escapeHTML(r.resolution_notes || 'All requested items/verifications have been fulfilled.')}</p>
      `;
    } else {
      resBox.style.display = 'none';
    }

    // Custom Category Details Grid
    const customGrid = document.getElementById('detailCustomFields');
    if (r.custom_data && Object.keys(r.custom_data).length > 0) {
      customGrid.innerHTML = Object.entries(r.custom_data).map(([k, v]) => `
        <div class="custom-field-item">
          <span class="cf-label">${k.replace(/_/g, ' ')}</span>
          <span class="cf-value">${this.escapeHTML(String(v))}</span>
        </div>
      `).join('');
      customGrid.style.display = 'grid';
    } else {
      customGrid.style.display = 'none';
    }

    // Attachments
    this.renderAttachmentsList();

    // Requester & Meta info
    document.getElementById('detailRequesterName').textContent = r.requester_name;
    document.getElementById('detailRequesterEmpId').textContent = r.requester_employee_id || 'N/A';
    document.getElementById('detailRequesterDept').textContent = r.requester_department || 'General';
    document.getElementById('detailRequesterEmail').textContent = r.requester_email;
    document.getElementById('detailAssigneeName').textContent = r.assignee_name || 'Unassigned';
    document.getElementById('detailCreatedAt').textContent = new Date(r.created_at).toLocaleString();
    document.getElementById('detailUpdatedAt').textContent = new Date(r.updated_at).toLocaleString();

    // Workflow actions box (Staff vs Employee)
    const isStaff = ['hr', 'payroll', 'it', 'admin'].includes(this.currentUser.role);
    const hrControls = document.getElementById('hrActionControlsBox');
    const empClose = document.getElementById('employeeCloseBox');
    const internalTab = document.getElementById('tabInternalNotes');
    const internalCheck = document.getElementById('internalCheckWrap');

    if (isStaff) {
      hrControls.style.display = 'block';
      document.getElementById('actionStatusSelect').value = r.status === 'submitted' ? 'under_review' : r.status;
      document.getElementById('actionAssignSelect').value = r.assigned_to || '';
      internalTab.style.display = '';
      internalCheck.style.display = 'flex';
      
      // Show Experience Letter generation button if applicable
      const genBox = document.getElementById('actionGenLetterBox');
      genBox.style.display = (r.category_id === 'experience_letter' && ['hr', 'admin'].includes(this.currentUser.role)) ? 'block' : 'none';
    } else {
      hrControls.style.display = 'none';
      internalTab.style.display = 'none';
      internalCheck.style.display = 'none';
    }

    // If employee and ticket is resolved, show Confirm & Close box
    if (!isStaff && r.status === 'resolved') {
      empClose.style.display = 'block';
    } else {
      empClose.style.display = 'none';
    }

    // Render Conversation Stream
    this.switchCommentTab('public');
  }

  updateStepperProgress(status) {
    const steps = ['submitted', 'under_review', 'in_progress', 'resolved', 'closed'];
    const nodeIds = {
      submitted: 'stepNodeSubmitted',
      under_review: 'stepNodeUnderReview',
      in_progress: 'stepNodeInProgress',
      resolved: 'stepNodeResolved',
      closed: 'stepNodeClosed'
    };

    let currentIndex = steps.indexOf(status);
    if (status === 'rejected' || status === 'on_hold') currentIndex = 2; // display intermediate

    steps.forEach((s, idx) => {
      const node = document.getElementById(nodeIds[s]);
      if (!node) return;
      node.classList.remove('completed', 'current');
      if (idx < currentIndex) node.classList.add('completed');
      else if (idx === currentIndex) node.classList.add('current');
    });

    for (let i = 1; i <= 4; i++) {
      const line = document.getElementById(`stepLine${i}`);
      if (line) {
        if (i <= currentIndex) line.classList.add('completed');
        else line.classList.remove('completed');
      }
    }
  }

  renderAttachmentsList() {
    const list = document.getElementById('detailAttachmentsList');
    const atts = this.activeRequestDetail?.attachments || [];
    if (atts.length === 0) {
      list.innerHTML = '<p class="text-muted text-sm">No files uploaded for this ticket.</p>';
      return;
    }

    list.innerHTML = atts.map(a => `
      <div class="att-card">
        <div class="att-left">
          <i class="fa-solid fa-file-lines att-icon"></i>
          <div>
            <div class="att-name">${this.escapeHTML(a.filename)}</div>
            <div class="att-size">${(a.file_size / 1024).toFixed(1)} KB • Uploaded by ${this.escapeHTML(a.uploader_name)}</div>
          </div>
        </div>
        <a href="/api/requests/${this.activeRequestDetail.id}/attachments/${a.id}/download" class="btn-secondary btn-sm" download>
          <i class="fa-solid fa-download"></i> Download
        </a>
      </div>
    `).join('');
  }

  switchCommentTab(tab) {
    this.activeCommentTab = tab;
    document.querySelectorAll('#commentFilterTabs .pill').forEach(p => p.classList.remove('active'));
    event?.target?.classList.add('active');

    const container = document.getElementById('detailCommentStream');
    const form = document.getElementById('commentPostForm');
    const comments = this.activeRequestDetail?.comments || [];
    const audits = this.activeRequestDetail?.audit_logs || [];

    if (tab === 'audit') {
      form.style.display = 'none';
      if (audits.length === 0) {
        container.innerHTML = '<p class="text-muted text-sm py-3 text-center">No audit logs recorded.</p>';
        return;
      }
      container.innerHTML = audits.map(a => `
        <div class="comment-bubble audit-entry">
          <div class="comment-header">
            <span class="comment-author text-info"><i class="fa-solid fa-shield-halved"></i> ${a.action}</span>
            <span class="comment-time">${new Date(a.created_at).toLocaleString()}</span>
          </div>
          <div class="comment-msg">${this.escapeHTML(a.details)}</div>
        </div>
      `).join('');
      return;
    }

    form.style.display = 'block';

    let filtered = comments;
    if (tab === 'public') {
      filtered = comments.filter(c => !c.is_internal);
    } else if (tab === 'internal') {
      filtered = comments.filter(c => c.is_internal);
    }

    if (filtered.length === 0) {
      container.innerHTML = `<p class="text-muted text-sm py-3 text-center">${tab === 'internal' ? 'No internal HR notes yet.' : 'No conversation messages yet. Start the conversation below.'}</p>`;
      return;
    }

    container.innerHTML = filtered.map(c => `
      <div class="comment-bubble ${c.is_internal ? 'internal-note' : ''}">
        <div class="comment-header">
          <span class="comment-author">
            ${this.escapeHTML(c.user_name)} 
            <span class="text-xs text-muted">(${c.user_role.toUpperCase()})</span>
            ${c.is_internal ? `<span class="internal-pill"><i class="fa-solid fa-lock"></i> HR INTERNAL NOTE</span>` : ''}
          </span>
          <span class="comment-time">${new Date(c.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
        </div>
        <div class="comment-msg">${this.escapeHTML(c.message)}</div>
      </div>
    `).join('');

    container.scrollTop = container.scrollHeight;
  }

  async handlePostComment(event) {
    event.preventDefault();
    const textInput = document.getElementById('commentInputText');
    const isInternal = document.getElementById('commentIsInternalCheckbox')?.checked || false;
    const msg = textInput.value.trim();
    if (!msg) return;

    try {
      const res = await fetch(`/api/requests/${this.activeRequestDetail.id}/comments`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.token}`
        },
        body: JSON.stringify({ message: msg, is_internal: isInternal })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to post message');
      }

      textInput.value = '';
      if (document.getElementById('commentIsInternalCheckbox')) {
        document.getElementById('commentIsInternalCheckbox').checked = false;
      }

      // Refresh detail modal
      await this.openRequestDetailModal(this.activeRequestDetail.id);
      this.showToast('Message posted', 'success');
    } catch (e) {
      this.showToast(e.message, 'error');
    }
  }

  async handleUploadExtraAttachment(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('attachment_type', 'supporting');

    try {
      const res = await fetch(`/api/requests/${this.activeRequestDetail.id}/attachments`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${this.token}` },
        body: formData
      });

      if (!res.ok) throw new Error('Failed to upload file');
      this.showToast(`Uploaded ${file.name}`, 'success');
      await this.openRequestDetailModal(this.activeRequestDetail.id);
    } catch (e) {
      this.showToast(e.message, 'error');
    }
  }

  handleStatusSelectChange() {
    const val = document.getElementById('actionStatusSelect').value;
    const reasonGroup = document.getElementById('actionReasonGroup');
    const reasonLabel = document.getElementById('actionReasonLabel');
    if (val === 'rejected') {
      reasonGroup.style.display = 'block';
      reasonLabel.textContent = 'Mandatory Rejection Reason';
      reasonLabel.className = 'form-label text-sm text-danger font-bold';
    } else if (val === 'resolved') {
      reasonGroup.style.display = 'block';
      reasonLabel.textContent = 'Resolution Summary & Notes';
      reasonLabel.className = 'form-label text-sm text-emerald font-bold';
    } else {
      reasonGroup.style.display = 'none';
    }
  }

  async submitStatusUpdate() {
    const newStatus = document.getElementById('actionStatusSelect').value;
    const notes = document.getElementById('actionReasonText')?.value || '';

    if (newStatus === 'rejected' && !notes.trim()) {
      this.showToast('Please provide a reason for rejection', 'error');
      return;
    }

    try {
      const res = await fetch(`/api/requests/${this.activeRequestDetail.id}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.token}`
        },
        body: JSON.stringify({ status: newStatus, reason_or_notes: notes })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Status transition failed');
      }

      this.showToast(`Status updated to ${newStatus.toUpperCase()}`, 'success');
      await this.openRequestDetailModal(this.activeRequestDetail.id);
      await this.fetchRequests();
    } catch (e) {
      this.showToast(e.message, 'error');
    }
  }

  async submitAssignment() {
    const staffId = document.getElementById('actionAssignSelect').value;
    try {
      const res = await fetch(`/api/requests/${this.activeRequestDetail.id}/assign`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.token}`
        },
        body: JSON.stringify({ assigned_to: staffId ? parseInt(staffId) : null })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Assignment failed');
      }

      this.showToast('Request assignment updated', 'success');
      await this.openRequestDetailModal(this.activeRequestDetail.id);
      await this.fetchRequests();
    } catch (e) {
      this.showToast(e.message, 'error');
    }
  }

  async generateOfficialExperienceLetter() {
    if (!confirm('Auto-generate formal Certificate of Employment with company seal and attach to ticket?')) return;
    try {
      const res = await fetch(`/api/requests/${this.activeRequestDetail.id}/generate-experience-letter`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${this.token}` }
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to generate letter');
      }

      const data = await res.json();
      this.showToast(data.message, 'success');
      await this.openRequestDetailModal(this.activeRequestDetail.id);
      await this.fetchRequests();
    } catch (e) {
      this.showToast(e.message, 'error');
    }
  }

  async closeRequestAsEmployee() {
    try {
      const res = await fetch(`/api/requests/${this.activeRequestDetail.id}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.token}`
        },
        body: JSON.stringify({ status: 'closed', reason_or_notes: 'Confirmed and closed by employee.' })
      });

      if (!res.ok) throw new Error('Failed to close request');
      this.showToast('Thank you! Ticket has been closed.', 'success');
      await this.openRequestDetailModal(this.activeRequestDetail.id);
      await this.fetchRequests();
    } catch (e) {
      this.showToast(e.message, 'error');
    }
  }

  /* ================= ANALYTICS & SLA ================= */

  async fetchAnalytics() {
    try {
      const res = await fetch('/api/analytics/dashboard', {
        headers: { 'Authorization': `Bearer ${this.token}` }
      });
      if (!res.ok) throw new Error('Failed to fetch analytics');
      const data = await res.json();
      this.renderAnalyticsView(data);
    } catch (e) {
      console.error(e);
      this.showToast('Error loading analytics', 'error');
    }
  }

  renderAnalyticsView(data) {
    document.getElementById('anTotal').textContent = data.total_requests;
    document.getElementById('anPending').textContent = data.pending_requests;
    document.getElementById('anProgress').textContent = data.in_progress_requests;
    document.getElementById('anResolved').textContent = data.resolved_requests + data.closed_requests;
    document.getElementById('anAvgHours').textContent = `${data.avg_resolution_hours} hrs`;
    document.getElementById('anOverdue').textContent = data.overdue_requests;

    // Category bars
    const catContainer = document.getElementById('catBarsList');
    if (catContainer) {
      const maxCat = Math.max(...Object.values(data.requests_by_category), 1);
      catContainer.innerHTML = Object.entries(data.requests_by_category).map(([name, count]) => {
        const pct = Math.round((count / maxCat) * 100);
        return `
          <div class="bar-row">
            <div class="bar-info">
              <span>${name}</span>
              <span class="font-bold">${count} requests</span>
            </div>
            <div class="bar-track">
              <div class="bar-fill" style="width: ${pct}%;"></div>
            </div>
          </div>
        `;
      }).join('');
    }

    // Priority bars
    const prioContainer = document.getElementById('prioBarsList');
    if (prioContainer) {
      const maxPrio = Math.max(...Object.values(data.requests_by_priority), 1);
      prioContainer.innerHTML = Object.entries(data.requests_by_priority).map(([prio, count]) => {
        const pct = Math.round((count / maxPrio) * 100);
        return `
          <div class="bar-row">
            <div class="bar-info">
              <span class="priority-badge priority-${prio}">${prio.toUpperCase()}</span>
              <span class="font-bold">${count} tickets</span>
            </div>
            <div class="bar-track">
              <div class="bar-fill bg-${prio === 'urgent' ? 'rose' : prio === 'high' ? 'amber' : 'blue'}" style="width: ${pct}%;"></div>
            </div>
          </div>
        `;
      }).join('');
    }

    // Audit logs table
    const auditTbody = document.getElementById('analyticsAuditBody');
    if (auditTbody) {
      auditTbody.innerHTML = data.recent_activity.map(a => `
        <tr>
          <td class="text-muted">${new Date(a.created_at).toLocaleString()}</td>
          <td class="font-bold">${this.escapeHTML(a.user_name || 'System')}</td>
          <td><span class="status-badge status-in_progress">${a.action}</span></td>
          <td>${this.escapeHTML(a.details)}</td>
          <td class="text-muted">${a.ip_address || '127.0.0.1'}</td>
        </tr>
      `).join('');
    }
  }

  /* ================= ADMIN CENTER ================= */

  async fetchAdminUsers() {
    try {
      const res = await fetch('/api/auth/users', {
        headers: { 'Authorization': `Bearer ${this.token}` }
      });
      if (!res.ok) throw new Error('Failed to fetch user directory');
      const users = await res.json();
      const tbody = document.getElementById('adminUsersBody');
      if (tbody) {
        tbody.innerHTML = users.map(u => `
          <tr>
            <td class="font-bold text-indigo">${u.employee_id || 'N/A'}</td>
            <td class="font-bold">${this.escapeHTML(u.full_name)}</td>
            <td>${this.escapeHTML(u.email)}</td>
            <td>${u.department || 'General'}</td>
            <td>${u.designation || 'Staff'}</td>
            <td><span class="status-badge status-${u.role === 'admin' ? 'rejected' : 'in_progress'}">${u.role.toUpperCase()}</span></td>
            <td class="text-muted">${new Date(u.created_at).toLocaleDateString()}</td>
          </tr>
        `).join('');
      }
    } catch (e) {
      console.error(e);
      this.showToast('Failed to load user directory', 'error');
    }
  }

  /* ================= NOTIFICATIONS ================= */

  async fetchNotifications(background = false) {
    try {
      const res = await fetch('/api/notifications', {
        headers: { 'Authorization': `Bearer ${this.token}` }
      });
      if (!res.ok) return;
      this.notifications = await res.json();
      
      const unread = this.notifications.filter(n => !n.is_read).length;
      const badge = document.getElementById('notifCount');
      if (badge) {
        badge.textContent = unread;
        badge.style.display = unread > 0 ? 'flex' : 'none';
      }

      this.renderNotificationList();
    } catch (e) {
      if (!background) console.error(e);
    }
  }

  renderNotificationList() {
    const container = document.getElementById('notifList');
    if (!container) return;

    if (this.notifications.length === 0) {
      container.innerHTML = '<div class="empty-notif">No notifications</div>';
      return;
    }

    container.innerHTML = this.notifications.map(n => `
      <div class="notif-item ${n.is_read ? '' : 'unread'}" onclick="app.handleNotifClick(${n.id}, ${n.request_id})">
        <div class="notif-item-title">${this.escapeHTML(n.title)}</div>
        <div class="notif-item-msg">${this.escapeHTML(n.message)}</div>
        <div class="notif-item-time">${new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
      </div>
    `).join('');
  }

  async handleNotifClick(notifId, requestId) {
    await fetch(`/api/notifications/${notifId}/read`, {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${this.token}` }
    });
    this.toggleNotifications();
    await this.fetchNotifications();
    if (requestId) {
      this.openRequestDetailModal(requestId);
    }
  }

  async markAllNotificationsRead() {
    await fetch('/api/notifications/read-all', {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${this.token}` }
    });
    await this.fetchNotifications();
    this.showToast('All notifications marked as read', 'info');
  }

  toggleNotifications() {
    const menu = document.getElementById('notifMenu');
    menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
  }

  toggleUserMenu() {
    const menu = document.getElementById('userDropdown');
    menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
  }

  closeUserMenu() {
    const menu = document.getElementById('userDropdown');
    if (menu) menu.style.display = 'none';
  }

  /* ================= MODAL UTILITIES ================= */

  openModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.style.display = 'flex';
  }

  closeModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.style.display = 'none';
  }

  openAuthModal(tab = 'login') {
    this.switchAuthTab(tab);
    this.openModal('authModal');
    this.closeUserMenu();
  }

  openNewUserModal() {
    this.openAuthModal('register');
  }

  switchAuthTab(tab) {
    document.getElementById('authTabLogin').classList.toggle('active', tab === 'login');
    document.getElementById('authTabRegister').classList.toggle('active', tab === 'register');
    document.getElementById('loginForm').style.display = tab === 'login' ? 'block' : 'none';
    document.getElementById('registerForm').style.display = tab === 'register' ? 'block' : 'none';
    document.getElementById('authModalTitle').textContent = tab === 'login' ? 'Sign In to NexusHR' : 'Create Organization Account';
  }

  /* ================= HELPERS & TOASTS ================= */

  getStatusLabel(status) {
    const map = {
      submitted: 'Submitted',
      under_review: 'Under Review',
      in_progress: 'In Progress',
      resolved: 'Resolved',
      closed: 'Closed',
      rejected: 'Rejected',
      on_hold: 'On Hold'
    };
    return map[status] || status;
  }

  getCategoryIcon(catId) {
    const map = {
      leave_clarification: 'calendar-days',
      payroll_query: 'file-invoice-dollar',
      experience_letter: 'award',
      asset_request: 'laptop',
      onboarding_request: 'user-plus'
    };
    return map[catId] || 'file';
  }

  escapeHTML(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = 'circle-info';
    if (type === 'success') icon = 'circle-check';
    if (type === 'error') icon = 'circle-exclamation';

    toast.innerHTML = `
      <i class="fa-solid fa-${icon}"></i>
      <span>${this.escapeHTML(message)}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = 'fadeOut 0.3s forwards';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }
}

// Global App Instance
const app = new NexusHRApp();

// Close dropdowns on outside click
window.addEventListener('click', (e) => {
  if (!e.target.closest('.notification-dropdown-container')) {
    const notifMenu = document.getElementById('notifMenu');
    if (notifMenu) notifMenu.style.display = 'none';
  }
  if (!e.target.closest('.user-profile-menu')) {
    const userMenu = document.getElementById('userDropdown');
    if (userMenu) userMenu.style.display = 'none';
  }
});
