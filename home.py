# import os
# import streamlit as st


# def render_home():

#     # ============================================================
#     # PAGE CSS
#     # ============================================================

#     st.markdown(
#         """
#         <style>

#         .home-title {
#             font-size: 38px;
#             font-weight: 800;
#             color: #12264f;
#             margin-bottom: 4px;
#         }

#         .home-subtitle {
#             font-size: 16px;
#             color: #667085;
#             margin-bottom: 22px;
#         }

#         .hero-image {
#             width: 100%;
#             border-radius: 18px;
#             border: 1px solid #e1e8f5;
#             box-shadow: 0 8px 30px rgba(30, 70, 130, 0.08);
#             margin-bottom: 28px;
#         }

#         .section-title {
#             font-size: 25px;
#             font-weight: 750;
#             color: #18213d;
#             margin-top: 12px;
#             margin-bottom: 5px;
#         }

#         .section-subtitle {
#             font-size: 14px;
#             color: #667085;
#             margin-bottom: 18px;
#         }

#         .module-card {
#             border: 1px solid #dce5f2;
#             border-radius: 14px;
#             padding: 20px;
#             background: white;
#             min-height: 155px;
#             box-shadow: 0 4px 15px rgba(30, 60, 110, 0.05);
#         }

#         .module-icon {
#             font-size: 28px;
#             margin-bottom: 8px;
#         }

#         .module-title {
#             font-size: 17px;
#             font-weight: 700;
#             color: #17345f;
#             margin-bottom: 7px;
#         }

#         .module-description {
#             font-size: 13px;
#             color: #667085;
#             line-height: 1.5;
#         }

#         .quick-title {
#             font-size: 22px;
#             font-weight: 750;
#             color: #18213d;
#             margin-top: 28px;
#             margin-bottom: 15px;
#         }

#         </style>
#         """,
#         unsafe_allow_html=True,
#     )

#     # ============================================================
#     # HEADER
#     # ============================================================

#     st.markdown(
#         """
#         <div class="home-title">
#             Welcome to SI-PLATFORM 👋
#         </div>

#         <div class="home-subtitle">
#             Kubernetes Automation & Validation Suite
#         </div>
#         """,
#         unsafe_allow_html=True,
#     )

#     # ============================================================
#     # HERO IMAGE
#     # ============================================================

#     image_path = os.path.join(
#         os.path.dirname(__file__),
#         "kubernetes_automation.png",
#     )

#     if os.path.exists(image_path):

#         st.image(
#             image_path,
#             use_container_width=True,
#         )

#     else:

#         st.warning(
#             "kubernetes_automation.png not found. "
#             "Keep the image in the same folder as home.py."
#         )

#     # ============================================================
#     # AFTER IMAGE - FUNCTIONAL OPTIONS
#     # ============================================================

#     st.markdown(
#         """
#         <div class="section-title">
#             Platform Operations
#         </div>

#         <div class="section-subtitle">
#             Quickly access Kubernetes validation, troubleshooting,
#             backup and automation capabilities.
#         </div>
#         """,
#         unsafe_allow_html=True,
#     )

#     # ============================================================
#     # ROW 1
#     # ============================================================

#     col1, col2, col3 = st.columns(3)

#     with col1:

#         st.markdown(
#             """
#             <div class="module-card">
#                 <div class="module-icon">🔗</div>
#                 <div class="module-title">
#                     Workload Comparator
#                 </div>
#                 <div class="module-description">
#                     Compare workloads between Kubernetes environments
#                     and identify missing or different workloads.
#                 </div>
#             </div>
#             """,
#             unsafe_allow_html=True,
#         )

#         if st.button(
#             "Open Workload Comparator →",
#             key="home_workload",
#             use_container_width=True,
#         ):
#             st.session_state.page = "Workload Comparator"
#             st.rerun()

#     with col2:

#         st.markdown(
#             """
#             <div class="module-card">
#                 <div class="module-icon">🐳</div>
#                 <div class="module-title">
#                     Docker Image Search
#                 </div>
#                 <div class="module-description">
#                     Find Kubernetes workload images and identify the
#                     RKE/RKE2 node where an image is available.
#                 </div>
#             </div>
#             """,
#             unsafe_allow_html=True,
#         )

#         if st.button(
#             "Open Docker Image Search →",
#             key="home_docker",
#             use_container_width=True,
#         ):
#             st.session_state.page = "Docker Image Search"
#             st.rerun()

#     with col3:

#         st.markdown(
#             """
#             <div class="module-card">
#                 <div class="module-icon">🔗</div>
#                 <div class="module-title">
#                     DB String
#                 </div>
#                 <div class="module-description">
#                     Discover MongoDB connection strings from Kubernetes
#                     Secrets and ConfigMaps by namespace.
#                 </div>
#             </div>
#             """,
#             unsafe_allow_html=True,
#         )

#         if st.button(
#             "Open DB String →",
#             key="home_db",
#             use_container_width=True,
#         ):
#             st.session_state.page = "DB String"
#             st.rerun()

#     # ============================================================
#     # ROW 2
#     # ============================================================

#     col4, col5, col6 = st.columns(3)

#     with col4:

#         st.markdown(
#             """
#             <div class="module-card">
#                 <div class="module-icon">🌐</div>
#                 <div class="module-title">
#                     Ingress Connectivity
#                 </div>
#                 <div class="module-description">
#                     Automatically discover ingress IPs by namespace
#                     and validate hostname-to-IP connectivity.
#                 </div>
#             </div>
#             """,
#             unsafe_allow_html=True,
#         )

#         if st.button(
#             "Open Ingress →",
#             key="home_ingress",
#             use_container_width=True,
#         ):
#             st.session_state.page = "Ingress"
#             st.rerun()

#     with col5:

#         st.markdown(
#             """
#             <div class="module-card">
#                 <div class="module-icon">🚦</div>
#                 <div class="module-title">
#                     Container Status
#                 </div>
#                 <div class="module-description">
#                     Detect Pending, ContainerCreating, ImagePullBackOff,
#                     ErrImagePull and other unhealthy pod states.
#                 </div>
#             </div>
#             """,
#             unsafe_allow_html=True,
#         )

#         if st.button(
#             "Open Container Status →",
#             key="home_container",
#             use_container_width=True,
#         ):
#             st.session_state.page = "Container Status"
#             st.rerun()

#     with col6:

#         st.markdown(
#             """
#             <div class="module-card">
#                 <div class="module-icon">💾</div>
#                 <div class="module-title">
#                     Namespace Backup
#                 </div>
#                 <div class="module-description">
#                     Backup Deployments, StatefulSets, images, ConfigMaps,
#                     Secrets, PVCs and Services namespace by namespace.
#                 </div>
#             </div>
#             """,
#             unsafe_allow_html=True,
#         )

#         if st.button(
#             "Open Namespace Backup →",
#             key="home_backup",
#             use_container_width=True,
#         ):
#             st.session_state.page = "Namespace Backup"
#             st.rerun()

#     # ============================================================
#     # ROW 3
#     # ============================================================

#     col7, col8, col9 = st.columns(3)

#     with col7:

#         st.markdown(
#             """
#             <div class="module-card">
#                 <div class="module-icon">🔗</div>
#                 <div class="module-title">
#                     VM Connectivity
#                 </div>
#                 <div class="module-description">
#                     Test RKE1 and RKE2 node-to-node connectivity and
#                     generate a complete connectivity matrix.
#                 </div>
#             </div>
#             """,
#             unsafe_allow_html=True,
#         )

#         if st.button(
#             "Open VM Connectivity →",
#             key="home_vm",
#             use_container_width=True,
#         ):
#             st.session_state.page = "VM Connectivity"
#             st.rerun()

#     with col8:

#         st.markdown(
#             """
#             <div class="module-card">
#                 <div class="module-icon">🔄</div>
#                 <div class="module-title">
#                     Pod Connectivity
#                 </div>
#                 <div class="module-description">
#                     Validate pod-to-pod overlay network connectivity
#                     across Kubernetes nodes.
#                 </div>
#             </div>
#             """,
#             unsafe_allow_html=True,
#         )

#         if st.button(
#             "Open Pod Connectivity →",
#             key="home_pod",
#             use_container_width=True,
#         ):
#             st.session_state.page = "Pod Connectivity"
#             st.rerun()

#     with col9:

#         st.markdown(
#             """
#             <div class="module-card">
#                 <div class="module-icon">⚡</div>
#                 <div class="module-title">
#                     Kubernetes Automation
#                 </div>
#                 <div class="module-description">
#                     Automate common Kubernetes operational and
#                     troubleshooting activities.
#                 </div>
#             </div>
#             """,
#             unsafe_allow_html=True,
#         )

#         if st.button(
#             "Open Automation →",
#             key="home_automation",
#             use_container_width=True,
#         ):
#             st.session_state.page = "Kubernetes Automation"
#             st.rerun()

#     # ============================================================
#     # QUICK ACTIONS
#     # ============================================================

#     st.markdown(
#         """
#         <div class="quick-title">
#             Quick Actions
#         </div>
#         """,
#         unsafe_allow_html=True,
#     )

#     q1, q2, q3, q4 = st.columns(4)

#     with q1:
#         if st.button(
#             "🔍 Check Failed Pods",
#             key="quick_failed_pods",
#             use_container_width=True,
#         ):
#             st.session_state.page = "Container Status"
#             st.rerun()

#     with q2:
#         if st.button(
#             "🐳 Find Docker Image",
#             key="quick_image",
#             use_container_width=True,
#         ):
#             st.session_state.page = "Docker Image Search"
#             st.rerun()

#     with q3:
#         if st.button(
#             "💾 Create Backup",
#             key="quick_backup",
#             use_container_width=True,
#         ):
#             st.session_state.page = "Namespace Backup"
#             st.rerun()

#     with q4:
#         if st.button(
#             "🌐 Test Connectivity",
#             key="quick_connectivity",
#             use_container_width=True,
#         ):
#             st.session_state.page = "VM Connectivity"
#             st.rerun()

#     # ============================================================
#     # FOOTER
#     # ============================================================

#     st.markdown(
#         """
#         <br>
#         <div style="
#             text-align:center;
#             color:#98A2B3;
#             font-size:12px;
#             padding:20px;
#         ">
#             SI-PLATFORM • Kubernetes Automation & Validation Suite
#         </div>
#         """,
#         unsafe_allow_html=True,
#     )



import os
import streamlit as st


def render_home():

    # ============================================================
    # PAGE CSS
    # ============================================================

    st.markdown(
        """
        <style>

        .home-title {
            font-size: 38px;
            font-weight: 800;
            color: #12264f;
            margin-bottom: 4px;
        }

        .home-subtitle {
            font-size: 16px;
            color: #667085;
            margin-bottom: 22px;
        }

        .hero-image {
            width: 100%;
            border-radius: 18px;
            border: 1px solid #e1e8f5;
            box-shadow: 0 8px 30px rgba(30, 70, 130, 0.08);
            margin-bottom: 28px;
        }

        .section-title {
            font-size: 25px;
            font-weight: 750;
            color: #18213d;
            margin-top: 12px;
            margin-bottom: 5px;
        }

        .section-subtitle {
            font-size: 14px;
            color: #667085;
            margin-bottom: 18px;
        }

        .module-card {
            border: 1px solid #dce5f2;
            border-radius: 14px;
            padding: 20px;
            background: white;
            min-height: 155px;
            box-shadow: 0 4px 15px rgba(30, 60, 110, 0.05);
        }

        .module-icon {
            font-size: 28px;
            margin-bottom: 8px;
        }

        .module-title {
            font-size: 17px;
            font-weight: 700;
            color: #17345f;
            margin-bottom: 7px;
        }

        .module-description {
            font-size: 13px;
            color: #667085;
            line-height: 1.5;
        }

        .quick-title {
            font-size: 22px;
            font-weight: 750;
            color: #18213d;
            margin-top: 28px;
            margin-bottom: 15px;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )

    # ============================================================
    # HEADER
    # ============================================================

    st.markdown(
        """
        <div class="home-title">
            Welcome to SI-PLATFORM 👋
        </div>

        <div class="home-subtitle">
            Kubernetes Automation & Validation Suite
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ============================================================
    # HERO IMAGE
    # ============================================================

    image_path = os.path.join(
        os.path.dirname(__file__),
        "kubernetes_automation.png",
    )

    if os.path.exists(image_path):

        st.image(
            image_path,
            use_container_width=True,
        )

    else:

        st.warning(
            "kubernetes_automation.png not found. "
            "Keep the image in the same folder as home.py."
        )

    # ============================================================
    # AFTER IMAGE - FUNCTIONAL OPTIONS
    # ============================================================

    st.markdown(
        """
        <div class="section-title">
            Platform Operations
        </div>

        <div class="section-subtitle">
            Quickly access Kubernetes validation, troubleshooting,
            backup and automation capabilities.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ============================================================
    # ROW 1
    # ============================================================

    col1, col2, col3 = st.columns(3)

    with col1:

        st.markdown(
            """
            <div class="module-card">
                <div class="module-icon">🔗</div>
                <div class="module-title">
                    Workload Comparator
                </div>
                <div class="module-description">
                    Compare workloads between Kubernetes environments
                    and identify missing or different workloads.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "Open Workload Comparator →",
            key="home_workload",
            use_container_width=True,
        ):
            st.session_state.page = "Workload Comparator"
            st.rerun()

    with col2:

        st.markdown(
            """
            <div class="module-card">
                <div class="module-icon">🐳</div>
                <div class="module-title">
                    Docker Image Search
                </div>
                <div class="module-description">
                    Find Kubernetes workload images and identify the
                    RKE/RKE2 node where an image is available.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "Open Docker Image Search →",
            key="home_docker",
            use_container_width=True,
        ):
            st.session_state.page = "Docker Image Search"
            st.rerun()

    with col3:

        st.markdown(
            """
            <div class="module-card">
                <div class="module-icon">🔗</div>
                <div class="module-title">
                    DB String
                </div>
                <div class="module-description">
                    Discover MongoDB connection strings from Kubernetes
                    Secrets and ConfigMaps by namespace.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "Open DB String →",
            key="home_db",
            use_container_width=True,
        ):
            st.session_state.page = "DB String"
            st.rerun()

    # ============================================================
    # ROW 2
    # ============================================================

    col4, col5, col6 = st.columns(3)

    with col4:

        st.markdown(
            """
            <div class="module-card">
                <div class="module-icon">🌐</div>
                <div class="module-title">
                    Ingress Connectivity
                </div>
                <div class="module-description">
                    Automatically discover ingress IPs by namespace
                    and validate hostname-to-IP connectivity.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "Open Ingress →",
            key="home_ingress",
            use_container_width=True,
        ):
            st.session_state.page = "Ingress"
            st.rerun()

    with col5:

        st.markdown(
            """
            <div class="module-card">
                <div class="module-icon">🚦</div>
                <div class="module-title">
                    Container Status
                </div>
                <div class="module-description">
                    Detect Pending, ContainerCreating, ImagePullBackOff,
                    ErrImagePull and other unhealthy pod states.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "Open Container Status →",
            key="home_container",
            use_container_width=True,
        ):
            st.session_state.page = "Container Status"
            st.rerun()

    with col6:

        st.markdown(
            """
            <div class="module-card">
                <div class="module-icon">💾</div>
                <div class="module-title">
                    Namespace Backup
                </div>
                <div class="module-description">
                    Backup Deployments, StatefulSets, images, ConfigMaps,
                    Secrets, PVCs and Services namespace by namespace.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "Open Namespace Backup →",
            key="home_backup",
            use_container_width=True,
        ):
            st.session_state.page = "Namespace Backup"
            st.rerun()

    # ============================================================
    # ROW 3
    # ============================================================

    col7, col8, col9 = st.columns(3)

    with col7:

        st.markdown(
            """
            <div class="module-card">
                <div class="module-icon">🔗</div>
                <div class="module-title">
                    VM Connectivity
                </div>
                <div class="module-description">
                    Test RKE1 and RKE2 node-to-node connectivity and
                    generate a complete connectivity matrix.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "Open VM Connectivity →",
            key="home_vm",
            use_container_width=True,
        ):
            st.session_state.page = "VM Connectivity"
            st.rerun()

    with col8:

        st.markdown(
            """
            <div class="module-card">
                <div class="module-icon">🔄</div>
                <div class="module-title">
                    Pod Connectivity
                </div>
                <div class="module-description">
                    Validate pod-to-pod overlay network connectivity
                    across Kubernetes nodes.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "Open Pod Connectivity →",
            key="home_pod",
            use_container_width=True,
        ):
            st.session_state.page = "Pod Connectivity"
            st.rerun()

    with col9:

        st.markdown(
            """
            <div class="module-card">
                <div class="module-icon">⚡</div>
                <div class="module-title">
                    Kubernetes Automation
                </div>
                <div class="module-description">
                    Automate common Kubernetes operational and
                    troubleshooting activities.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "Open Automation →",
            key="home_automation",
            use_container_width=True,
        ):
            st.session_state.page = "Kubernetes Automation"
            st.rerun()

    # ============================================================
    # QUICK ACTIONS
    # ============================================================

    st.markdown(
        """
        <div class="quick-title">
            Quick Actions
        </div>
        """,
        unsafe_allow_html=True,
    )

    q1, q2, q3, q4 = st.columns(4)

    with q1:
        if st.button(
            "🔍 Check Failed Pods",
            key="quick_failed_pods",
            use_container_width=True,
        ):
            st.session_state.page = "Container Status"
            st.rerun()

    with q2:
        if st.button(
            "🐳 Find Docker Image",
            key="quick_image",
            use_container_width=True,
        ):
            st.session_state.page = "Docker Image Search"
            st.rerun()

    with q3:
        if st.button(
            "💾 Create Backup",
            key="quick_backup",
            use_container_width=True,
        ):
            st.session_state.page = "Namespace Backup"
            st.rerun()

    with q4:
        if st.button(
            "🌐 Test Connectivity",
            key="quick_connectivity",
            use_container_width=True,
        ):
            st.session_state.page = "VM Connectivity"
            st.rerun()

    # ============================================================
    # FOOTER
    # ============================================================

    st.markdown(
        """
        <br>
        <div style="
            text-align:center;
            color:#98A2B3;
            font-size:12px;
            padding:20px;
        ">
            SI-PLATFORM • Kubernetes Automation & Validation Suite
        </div>
        """,
        unsafe_allow_html=True,
    )