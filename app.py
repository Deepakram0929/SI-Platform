import streamlit as st
import importlib
import sys
from pathlib import Path


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="SI-PLATFORM",
    page_icon="☸️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# GLOBAL CSS
# ============================================================

st.markdown(
    """
    <style>
    /* -----------------------------
       APP / MAIN AREA
       ----------------------------- */
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 52% 14%,
                rgba(66, 132, 255, 0.075),
                transparent 31%),
            linear-gradient(135deg,
                #f7fbff 0%,
                #ffffff 52%,
                #f4f8ff 100%);
    }

    [data-testid="stMain"] {
        background:
            radial-gradient(circle at 50% 16%,
                rgba(62, 128, 255, 0.045),
                transparent 34%);
    }

    .block-container {
        max-width: 100%;
        padding-top: 0.85rem !important;
        padding-left: 1.35rem !important;
        padding-right: 1.35rem !important;
        padding-bottom: 2rem !important;
    }

    /* -----------------------------
       SIDEBAR
       ----------------------------- */
    [data-testid="stSidebar"] {
        background:
            linear-gradient(180deg,
                #f8fbff 0%,
                #f2f7ff 100%);
        border-right: 1px solid #dce7f5;
        box-shadow: 4px 0 18px rgba(26, 82, 155, 0.035);
    }

    [data-testid="stSidebar"] > div:first-child {
        width: 220px !important;
    }

    [data-testid="stSidebar"] .block-container {
        padding: 0.85rem 0.65rem 1rem 0.65rem !important;
    }

    /* -----------------------------
       SIDEBAR BRAND
       ----------------------------- */
    .si-sidebar-brand {
        display: flex;
        align-items: center;
        gap: 9px;
        padding: 3px 5px 4px 5px;
        margin-bottom: 4px;
    }

    .si-brand-logo {
        width: 35px;
        height: 35px;
        min-width: 35px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(145deg, #1169f4, #1749bf);
        color: #ffffff;
        font-size: 19px;
        box-shadow: 0 5px 14px rgba(24, 94, 218, 0.22);
    }

    .si-brand-title {
        color: #14275a;
        font-size: 18px;
        font-weight: 800;
        line-height: 1.05;
    }

    .si-brand-subtitle {
        color: #7182a0;
        font-size: 9px;
        margin-top: 4px;
        letter-spacing: 0.2px;
    }

    /* -----------------------------
       SIDEBAR SECTION
       ----------------------------- */
    .si-nav-section {
        margin: 17px 5px 7px 5px;
        padding-bottom: 6px;
        border-bottom: 1px solid #e0e8f4;
        color: #7c8eac;
        font-size: 9px;
        font-weight: 800;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    /* -----------------------------
       SIDEBAR BUTTONS
       ----------------------------- */
    [data-testid="stSidebar"] .stButton {
        margin: 0 !important;
    }

    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        min-height: 34px !important;
        margin: 2px 0 !important;
        padding: 5px 8px !important;
        border: 1px solid transparent !important;
        border-radius: 8px !important;
        background: transparent !important;
        color: #29466e !important;
        box-shadow: none !important;
        text-align: left !important;
        justify-content: flex-start !important;
        font-size: 11.5px !important;
        font-weight: 600 !important;
        line-height: 1.2 !important;
        white-space: normal !important;
        transition: all 0.15s ease;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        background: #eaf3ff !important;
        border-color: #d5e5fb !important;
        color: #075ee0 !important;
    }

    /* -----------------------------
       ACTIVE NAV ITEM
       ----------------------------- */
    .si-nav-active {
        display: flex;
        align-items: center;
        width: 100%;
        min-height: 34px;
        box-sizing: border-box;
        margin: 2px 0;
        padding: 5px 8px;
        border: 1px solid #d8e7fc;
        border-radius: 8px;
        background: linear-gradient(90deg, #e9f3ff, #f2f8ff);
        color: #075ee0;
        font-size: 11.5px;
        font-weight: 700;
        line-height: 1.2;
        box-shadow: 0 2px 8px rgba(35, 105, 220, 0.06);
    }

    /* -----------------------------
       EXPANDERS
       ----------------------------- */
    [data-testid="stSidebar"] [data-testid="stExpander"] {
        border: 0 !important;
        border-radius: 8px !important;
        background: transparent !important;
        margin: 2px 0 !important;
    }

    [data-testid="stSidebar"] [data-testid="stExpander"] summary {
        padding: 9px 8px !important;
        color: #4f6788 !important;
        font-size: 11px !important;
        font-weight: 800 !important;
        letter-spacing: 0.9px !important;
        text-transform: uppercase !important;
    }

    [data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {
        background: #edf4ff !important;
        color: #1266df !important;
        border-radius: 8px !important;
    }

    [data-testid="stSidebar"] [data-testid="stExpanderDetails"] {
        padding: 2px 0 4px 0 !important;
    }

    [data-testid="stSidebar"] [data-testid="stExpander"] .stButton > button {
        min-height: 32px !important;
        padding: 5px 8px 5px 16px !important;
    }

    /* -----------------------------
       SIDEBAR DIVIDER
       ----------------------------- */
    .si-sidebar-divider {
        height: 1px;
        margin: 12px 5px 3px 5px;
        background: #e0e8f4;
    }

    /* -----------------------------
       MOBILE / NARROW SCREEN
       ----------------------------- */
    @media (max-width: 900px) {
        .block-container {
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# SAFE MODULE LOADER
# ============================================================

def load_function(module_name, function_name):

    try:

        # ----------------------------------------------------
        # Reload module during development
        # ----------------------------------------------------

        if module_name in sys.modules:

            module = importlib.reload(
                sys.modules[module_name]
            )

        else:

            module = importlib.import_module(
                module_name
            )

        # ----------------------------------------------------
        # Get function
        # ----------------------------------------------------

        function = getattr(
            module,
            function_name,
            None
        )

        if function is None:

            return (
                None,
                (
                    f"Function '{function_name}' "
                    f"was not found in "
                    f"'{module_name}.py'."
                )
            )

        if not callable(function):

            return (
                None,
                (
                    f"'{function_name}' exists in "
                    f"'{module_name}.py' "
                    f"but is not callable."
                )
            )

        return function, None

    except Exception as exc:

        return (
            None,
            f"{type(exc).__name__}: {exc}"
        )


# ============================================================
# LOAD MODULES
# ============================================================

render_home, home_error = load_function(
    "home",
    "render_home"
)


render_workload_comparator, workload_error = load_function(
    "workload_comparator",
    "render_workload_comparator"
)


render_image_comparator, image_error = load_function(
    "image_comparator",
    "render_image_comparator"
)


render_yaml_comparator, yaml_error = load_function(
    "yaml_comparator",
    "render_yaml_comparator"
)


# ============================================================
# ENVIRONMENT COMPARATOR
# ============================================================

render_environment_comparator, environment_error = load_function(
    "environment_comparator",
    "render_environment_comparator"
)


# ============================================================
# CPU & MEMORY
# ============================================================

render_cpu_memory, cpu_memory_error = load_function(
    "cpu_memory",
    "render_cpu_memory"
)


# ============================================================
# CLUSTER COMPARISON REPORT
# ============================================================

render_cluster_comparison_report, report_error = load_function(
    "cluster_comparison_report",
    "render_cluster_comparison_report"
)


render_docker_image_load, docker_error = load_function(
    "docker_image_load",
    "render_docker_image_load"
)


render_db_string, db_error = load_function(
    "db_string",
    "render_db_string"
)


render_ingress, ingress_error = load_function(
    "ingress",
    "render_ingress"
)


render_container_status, container_error = load_function(
    "container_status",
    "render_container_status"
)


render_namespace_backup, backup_error = load_function(
    "namespace_backup",
    "render_namespace_backup"
)


render_vm_connectivity, vm_error = load_function(
    "vm_connectivity",
    "render_vm_connectivity"
)


# ============================================================
# PAGE STATE
# ============================================================

if "page" not in st.session_state:

    st.session_state.page = "Home"


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    # ========================================================
    # BRAND
    # ========================================================

    st.markdown(
        """
        <div class="si-sidebar-brand">
            <div class="si-brand-logo">☸</div>
            <div>
                <div class="si-brand-title">SI-PLATFORM</div>
                <div class="si-brand-subtitle">K8s Automation Suite</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


    # ========================================================
    # SIDEBAR NAVIGATION FUNCTION
    # ========================================================

    def sidebar_nav(label, page, key):

        """Existing page routing with compact left-aligned navigation."""

        if st.session_state.page == page:

            st.markdown(
                f'<div class="si-nav-active">{label}</div>',
                unsafe_allow_html=True,
            )

        else:

            if st.button(
                label,
                key=key,
                use_container_width=True,
            ):

                st.session_state.page = page

                st.rerun()


    # ========================================================
    # VALIDATION & COMPARISON
    # ========================================================

    st.markdown(
        '<div class="si-nav-section">'
        'Validation &amp; Comparison'
        '</div>',
        unsafe_allow_html=True,
    )


    sidebar_nav(
        "⌂  Home",
        "Home",
        "nav_home"
    )


    sidebar_nav(
        "⚖ Environment Comparator",
        "Environment Comparator",
        "nav_environment",
    )


    sidebar_nav(
        "◇  Workload Comparator",
        "Workload Comparator",
        "nav_workload",
    )


    sidebar_nav(
        "▣  Image Comparator",
        "Image Comparator",
        "nav_image",
    )


    sidebar_nav(
        "📄  YAML Comparator",
        "YAML Comparator",
        "nav_yaml",
    )
    
    sidebar_nav(
        "⚙  CPU & MEM Compare",
        "CPU & Memory",
        "nav_cpu_memory",
    )


    # ========================================================
    # MONITORING & DIAGNOSTICS
    # ========================================================

    with st.expander(
        "🔎  Monitoring & Diagnostics",
        expanded=False
    ):

        sidebar_nav(
            "◎  Ingress Connectivity",
            "Ingress",
            "nav_ingress",
        )


        sidebar_nav(
            "⚙  Container Status",
            "Container Status",
            "nav_container_status",
        )


        sidebar_nav(
            "⌁  VM Connectivity",
            "VM Connectivity",
            "nav_vm_connectivity",
        )


        sidebar_nav(
            "🐳  Docker Image Search",
            "Docker Image Load",
            "nav_docker",
        )


    # ========================================================
    # BACKUP & OPERATIONS
    # ========================================================

    with st.expander(
        "💾  Backup & Operations",
        expanded=False
    ):

        sidebar_nav(
            "⇩  Namespace Backup",
            "Namespace Backup",
            "nav_namespace_backup",
        )


        sidebar_nav(
            "⌘  DB String",
            "DB String",
            "nav_db_string",
        )


    # ========================================================
    # REPORTS
    # ========================================================

    with st.expander(
        "📊  Reports",
        expanded=False
    ):

        sidebar_nav(
            "▣  Cluster Comparison Report",
            "Cluster Comparison Report",
            "nav_cluster_report",
        )


    # ========================================================
    # SIDEBAR DIVIDER
    # ========================================================

    st.markdown(
        '<div class="si-sidebar-divider"></div>',
        unsafe_allow_html=True,
    )


# ============================================================
# PAGE ROUTING
# ============================================================


# ============================================================
# HOME
# ============================================================

if st.session_state.page == "Home":

    if render_home:

        render_home()

    else:

        st.error(
            "Home module cannot be loaded."
        )

        if home_error:
            st.code(home_error)


# ============================================================
# WORKLOAD COMPARATOR
# ============================================================

elif st.session_state.page == "Workload Comparator":

    if render_workload_comparator:

        render_workload_comparator()

    else:

        st.error(
            "Workload Comparator cannot be loaded."
        )

        if workload_error:
            st.code(workload_error)

        st.info(
            "Make sure workload_comparator.py contains:"
        )

        st.code(
            """
def render_workload_comparator():

    # Workload Comparator code

    pass
            """,
            language="python"
        )


# ============================================================
# IMAGE COMPARATOR
# ============================================================

elif st.session_state.page == "Image Comparator":

    if render_image_comparator:

        render_image_comparator()

    else:

        st.error(
            "Image Comparator cannot be loaded."
        )

        if image_error:
            st.code(image_error)

        st.info(
            "Make sure image_comparator.py contains:"
        )

        st.code(
            """
def render_image_comparator():

    # Image Comparator code

    pass
            """,
            language="python"
        )


# ============================================================
# YAML COMPARATOR
# ============================================================

elif st.session_state.page == "YAML Comparator":

    if render_yaml_comparator:

        render_yaml_comparator()

    else:

        st.error(
            "YAML Comparator cannot be loaded."
        )

        if yaml_error:
            st.code(yaml_error)

        st.info(
            "Make sure yaml_comparator.py contains:"
        )

        st.code(
            """
def render_yaml_comparator():

    # Kubernetes YAML Comparator code

    pass
            """,
            language="python"
        )


# ============================================================
# CPU & MEMORY
# ============================================================

elif st.session_state.page == "CPU & Memory":

    if render_cpu_memory:

        render_cpu_memory()

    else:

        st.error(
            "CPU & Memory module cannot be loaded."
        )

        if cpu_memory_error:
            st.code(cpu_memory_error)

        st.info(
            "Make sure cpu_memory.py contains:"
        )

        st.code(
            """
def render_cpu_memory():

    # CPU & Memory code

    pass
            """,
            language="python"
        )


# ============================================================
# ENVIRONMENT COMPARATOR
# ============================================================

elif st.session_state.page == "Environment Comparator":

    if render_environment_comparator:

        render_environment_comparator()

    else:

        st.error(
            "Environment Comparator cannot be loaded."
        )

        if environment_error:
            st.code(environment_error)

        st.info(
            "Make sure environment_comparator.py contains:"
        )

        st.code(
            """
def render_environment_comparator():

    # UAT → PROD environment
    # comparison and sync code

    pass
            """,
            language="python"
        )


# ============================================================
# CLUSTER COMPARISON REPORT
# ============================================================

elif st.session_state.page == "Cluster Comparison Report":

    if render_cluster_comparison_report:

        render_cluster_comparison_report()

    else:

        st.error(
            "Cluster Comparison Report cannot be loaded."
        )

        if report_error:
            st.code(report_error)

        st.info(
            "Make sure cluster_comparison_report.py contains:"
        )

        st.code(
            """
def render_cluster_comparison_report():

    # Cluster Comparison Report code

    pass
            """,
            language="python"
        )


# ============================================================
# DOCKER IMAGE SEARCH
# ============================================================

elif st.session_state.page == "Docker Image Load":

    if render_docker_image_load:

        render_docker_image_load()

    else:

        st.error(
            "Docker Image Search module cannot be loaded."
        )

        if docker_error:
            st.code(docker_error)


# ============================================================
# DB STRING
# ============================================================

elif st.session_state.page == "DB String":

    if render_db_string:

        render_db_string()

    else:

        st.error(
            "DB String module cannot be loaded."
        )

        if db_error:
            st.code(db_error)


# ============================================================
# INGRESS
# ============================================================

elif st.session_state.page == "Ingress":

    if render_ingress:

        render_ingress()

    else:

        st.error(
            "Ingress module cannot be loaded."
        )

        if ingress_error:
            st.code(ingress_error)


# ============================================================
# CONTAINER STATUS
# ============================================================

elif st.session_state.page == "Container Status":

    if render_container_status:

        render_container_status()

    else:

        st.error(
            "Container Status module cannot be loaded."
        )

        if container_error:
            st.code(container_error)


# ============================================================
# NAMESPACE BACKUP
# ============================================================

elif st.session_state.page == "Namespace Backup":

    if render_namespace_backup:

        render_namespace_backup()

    else:

        st.error(
            "Namespace Backup module cannot be loaded."
        )

        if backup_error:
            st.code(backup_error)


# ============================================================
# VM CONNECTIVITY
# ============================================================

elif st.session_state.page == "VM Connectivity":

    if render_vm_connectivity:

        render_vm_connectivity()

    else:

        st.error(
            "VM Connectivity module cannot be loaded."
        )

        if vm_error:
            st.code(vm_error)


# ============================================================
# UNKNOWN PAGE
# ============================================================

else:

    st.warning(
        f"Unknown page: {st.session_state.page}"
    )

    st.session_state.page = "Home"

    st.rerun()