import streamlit as st
import importlib
import sys


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

    /* ========================================================
       SIDEBAR
       ======================================================== */

    [data-testid="stSidebar"] {
        background: #f7faff;
        border-right: 1px solid #dbe5f3;
    }

    [data-testid="stSidebar"] .block-container {
        padding-top: 1.2rem;
    }


    /* ========================================================
       SIDEBAR BRAND
       ======================================================== */

    .sidebar-brand {
        padding: 8px 12px 20px 12px;
    }

    .sidebar-brand-title {
        font-size: 18px;
        font-weight: 700;
        color: #17345f;
    }

    .sidebar-brand-subtitle {
        font-size: 10px;
        color: #7890b5;
        letter-spacing: 1.2px;
        margin-top: 3px;
    }


    /* ========================================================
       SIDEBAR SECTION
       ======================================================== */

    .sidebar-section {
        font-size: 10px;
        font-weight: 700;
        color: #7890b5;
        letter-spacing: 2px;
        margin: 10px 12px 8px 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #dbe5f3;
    }


    /* ========================================================
       SIDEBAR BUTTONS
       ======================================================== */

    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        text-align: left;

        border: 1px solid #d6deea;
        background: #ffffff;
        color: #18345e;

        border-radius: 8px;
        margin-bottom: 8px;

        min-height: 44px;

        font-size: 14px;
        font-weight: 600;

        transition: all 0.15s ease;
    }


    [data-testid="stSidebar"] .stButton > button:hover {
        border-color: #9ab8e8;
        background: #eef5ff;
        color: #0f4da8;
    }


    /* ========================================================
       MAIN PAGE
       ======================================================== */

    .page-title {
        font-size: 36px;
        font-weight: 700;
        color: #18213d;
    }

    .page-subtitle {
        font-size: 16px;
        color: #667085;
        margin-bottom: 24px;
    }


    /* ========================================================
       ERROR BOX
       ======================================================== */

    .module-error {
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #f1b5b5;
        background: #fff5f5;
        margin-bottom: 20px;
    }


    /* ========================================================
       STATUS BOX
       ======================================================== */

    .module-status {
        padding: 15px;
        border-radius: 8px;
        background: #eef7ff;
        border: 1px solid #c9def5;
        margin-bottom: 15px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SAFE MODULE LOADER
# ============================================================

def load_function(module_name, function_name):
    """
    Safely import/reload a module and return the requested function.

    Returns:
        (function, None) if successful
        (None, error_message) if unsuccessful
    """

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
        # Get requested function
        # ----------------------------------------------------

        function = getattr(
            module,
            function_name,
            None,
        )


        # ----------------------------------------------------
        # Function not found
        # ----------------------------------------------------

        if function is None:

            return (
                None,
                (
                    f"Function '{function_name}' "
                    f"was not found in '{module_name}.py'."
                ),
            )


        # ----------------------------------------------------
        # Verify callable
        # ----------------------------------------------------

        if not callable(function):

            return (
                None,
                (
                    f"'{function_name}' exists in "
                    f"'{module_name}.py' but is not callable."
                ),
            )


        return function, None


    except Exception as exc:

        return (
            None,
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# LOAD APPLICATION MODULES
# ============================================================

render_home, home_error = load_function(
    "home",
    "render_home",
)


# ============================================================
# WORKLOAD COMPARATOR
# ============================================================

render_workload_comparator, workload_error = (
    load_function(
        "workload_comparator",
        "render_workload_comparator",
    )
)


# ============================================================
# IMAGE COMPARATOR
# ============================================================

render_image_comparator, image_error = (
    load_function(
        "image_comparator",
        "render_image_comparator",
    )
)


# ============================================================
# DOCKER IMAGE SEARCH
# ============================================================

render_docker_image_load, docker_error = (
    load_function(
        "docker_image_load",
        "render_docker_image_load",
    )
)


# ============================================================
# DB STRING
# ============================================================

render_db_string, db_error = load_function(
    "db_string",
    "render_db_string",
)


# ============================================================
# INGRESS
# ============================================================

render_ingress, ingress_error = load_function(
    "ingress",
    "render_ingress",
)


# ============================================================
# CONTAINER STATUS
# ============================================================

render_container_status, container_error = (
    load_function(
        "container_status",
        "render_container_status",
    )
)


# ============================================================
# NAMESPACE BACKUP
# ============================================================

render_namespace_backup, backup_error = (
    load_function(
        "namespace_backup",
        "render_namespace_backup",
    )
)


# ============================================================
# VM CONNECTIVITY
# ============================================================

render_vm_connectivity, vm_error = (
    load_function(
        "vm_connectivity",
        "render_vm_connectivity",
    )
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

    st.html(
        """
        <div class="sidebar-brand">

            <div class="sidebar-brand-title">
                ☰ &nbsp; SI-PLATFORM
            </div>

            <div class="sidebar-brand-subtitle">
                AUTOMATION & VALIDATION SUITE
            </div>

        </div>
        """
    )


    # ========================================================
    # OPERATIONS
    # ========================================================

    st.html(
        """
        <div class="sidebar-section">
            OPERATIONS
        </div>
        """
    )


    # ========================================================
    # HOME
    # ========================================================

    if st.button(
        "🏠  Home",
        key="sidebar_home",
        use_container_width=True,
    ):

        st.session_state.page = "Home"
        st.rerun()


    # ========================================================
    # WORKLOAD COMPARATOR
    # ========================================================

    if st.button(
        "☸️  Workload Comparator",
        key="sidebar_workload",
        use_container_width=True,
    ):

        st.session_state.page = "Workload Comparator"
        st.rerun()


    # ========================================================
    # IMAGE COMPARATOR
    # ========================================================

    if st.button(
        "🐳  Image Comparator",
        key="sidebar_image_comparator",
        use_container_width=True,
    ):

        st.session_state.page = "Image Comparator"
        st.rerun()


    # ========================================================
    # DOCKER IMAGE SEARCH
    # ========================================================

    if st.button(
        "🐳  Docker Image Search",
        key="sidebar_docker",
        use_container_width=True,
    ):

        st.session_state.page = "Docker Image Load"
        st.rerun()


    # ========================================================
    # DB STRING
    # ========================================================

    if st.button(
        "🔗  DB String",
        key="sidebar_db_string",
        use_container_width=True,
    ):

        st.session_state.page = "DB String"
        st.rerun()


    # ========================================================
    # INGRESS
    # ========================================================

    if st.button(
        "🌐  Ingress",
        key="sidebar_ingress",
        use_container_width=True,
    ):

        st.session_state.page = "Ingress"
        st.rerun()


    # ========================================================
    # CONTAINER STATUS
    # ========================================================

    if st.button(
        "🚦  Container Status",
        key="sidebar_container_status",
        use_container_width=True,
    ):

        st.session_state.page = "Container Status"
        st.rerun()


    # ========================================================
    # NAMESPACE BACKUP
    # ========================================================

    if st.button(
        "💾  Namespace Backup",
        key="sidebar_namespace_backup",
        use_container_width=True,
    ):

        st.session_state.page = "Namespace Backup"
        st.rerun()


    # ========================================================
    # VM CONNECTIVITY
    # ========================================================

    if st.button(
        "🔗  VM Connectivity",
        key="sidebar_vm_connectivity",
        use_container_width=True,
    ):

        st.session_state.page = "VM Connectivity"
        st.rerun()


    # ========================================================
    # CONFIGURATION
    # ========================================================

    st.html(
        """
        <div class="sidebar-section">
            CONFIGURATION
        </div>
        """
    )

    st.caption(
        "Additional modules can be added here."
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

        st.code(
            home_error or
            "Unknown home module error."
        )


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

        st.code(
            workload_error or
            "Unknown workload_comparator error."
        )

        st.info(
            "Check workload_comparator.py. "
            "It must contain:"
        )

        st.code(
            """
def render_workload_comparator():

    # Workload Comparator code

    pass
            """,
            language="python",
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

        st.code(
            image_error or
            "Unknown image_comparator error."
        )

        st.info(
            "Check image_comparator.py. "
            "It must contain:"
        )

        st.code(
            """
def render_image_comparator():

    # Image Comparator code

    pass
            """,
            language="python",
        )


# ============================================================
# DOCKER IMAGE LOAD
# ============================================================

elif st.session_state.page == "Docker Image Load":

    if render_docker_image_load:

        render_docker_image_load()

    else:

        st.error(
            "Docker Image module cannot be loaded."
        )

        st.code(
            docker_error or
            "Unknown docker_image_load error."
        )


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

        st.code(
            db_error or
            "Unknown db_string error."
        )


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

        st.code(
            ingress_error or
            "Unknown ingress error."
        )


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

        st.code(
            container_error or
            "Unknown container_status error."
        )


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

        st.code(
            backup_error or
            "Unknown namespace_backup error."
        )


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

        st.code(
            vm_error or
            "Unknown vm_connectivity error."
        )


# ============================================================
# UNKNOWN PAGE
# ============================================================

else:

    st.warning(
        f"Unknown page: {st.session_state.page}"
    )

    st.session_state.page = "Home"

    st.rerun()