import streamlit as st
import yaml
from html import escape
from textwrap import dedent


# ============================================================
# CONFIGURATION
# ============================================================

RESOURCE_TYPES = [
    "Deployment",
    "ConfigMap",
    "Secret",
    "StatefulSet",
    "DaemonSet",
    "Job",
    "CronJob",
    "Service",
    "Ingress",
    "PersistentVolumeClaim",
]

MAX_FILE_SIZE = 200 * 1024 * 1024


# ============================================================
# PAGE CONFIGURATION
# ============================================================

def configure_page():

    st.set_page_config(
        page_title="YAML Comparator",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded",
    )


# ============================================================
# GLOBAL CSS
# ============================================================

def load_css():

    st.markdown(
        """
<style>

/* ============================================================
   PAGE
   ============================================================ */

.yaml-page-title {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 5px;
}

.yaml-page-icon {
    font-size: 42px;
    line-height: 1;
}

.yaml-page-title-text {
    font-size: 36px;
    font-weight: 700;
    color: #18213d;
}

.yaml-page-subtitle {
    font-size: 16px;
    color: #667085;
    margin-bottom: 30px;
}


/* ============================================================
   SECTION
   ============================================================ */

.yaml-section-title {
    font-size: 25px;
    font-weight: 700;
    color: #18213d;
    margin-top: 20px;
    margin-bottom: 10px;
}


/* ============================================================
   INFO BOX
   ============================================================ */

.yaml-info-box {
    background: #f7faff;
    border: 1px solid #c9dcff;
    border-radius: 10px;
    padding: 20px 24px;
    margin: 22px 0;
}

.yaml-info-title {
    font-size: 18px;
    font-weight: 700;
    color: #17345f;
    margin-bottom: 10px;
}

.yaml-info-text {
    font-size: 14px;
    color: #667085;
    line-height: 1.7;
}


/* ============================================================
   UPLOAD SECTION
   ============================================================ */

.yaml-upload-title {
    font-size: 23px;
    font-weight: 700;
    color: #18213d;
    margin-bottom: 5px;
}

.yaml-upload-subtitle {
    font-size: 14px;
    color: #667085;
    margin-bottom: 10px;
}


/* ============================================================
   FILE STATUS
   ============================================================ */

.yaml-file-status {
    padding: 11px 15px;
    margin-top: 10px;
    margin-bottom: 10px;
    border-radius: 8px;
    background: #ecfdf3;
    border: 1px solid #abefc6;
    color: #027a48;
    font-size: 14px;
}


/* ============================================================
   SUMMARY
   ============================================================ */

.yaml-summary-container {
    display: flex;
    gap: 15px;
    margin: 25px 0;
}

.yaml-summary-card {
    flex: 1;
    background: #ffffff;
    border: 1px solid #dbe5f3;
    border-radius: 10px;
    padding: 17px 20px;
}

.yaml-summary-label {
    color: #667085;
    font-size: 13px;
    margin-bottom: 5px;
}

.yaml-summary-number {
    color: #18213d;
    font-size: 30px;
    font-weight: 700;
}


/* ============================================================
   RESOURCE HEADER
   ============================================================ */

.resource-header {
    background: #f7faff;
    border: 1px solid #dbe5f3;
    border-radius: 8px 8px 0 0;
    padding: 14px 17px;
    font-size: 16px;
    font-weight: 700;
    color: #18213d;
    margin-top: 25px;
}


/* ============================================================
   TABLE
   ============================================================ */

.yaml-diff-wrapper {
    width: 100%;
    overflow-x: auto;
    margin-bottom: 25px;
}

.yaml-diff-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    font-size: 14px;
}

.yaml-diff-table th {
    background: #eef3f9;
    color: #344054;
    font-weight: 700;
    text-align: left;
    padding: 12px 14px;
    border: 1px solid #d0d5dd;
}

.yaml-diff-table td {
    padding: 12px 14px;
    border: 1px solid #d0d5dd;
    vertical-align: top;
    word-break: break-word;
    white-space: pre-wrap;
}

.yaml-diff-table th:nth-child(1) {
    width: 28%;
}

.yaml-diff-table th:nth-child(2) {
    width: 28%;
}

.yaml-diff-table th:nth-child(3) {
    width: 28%;
}

.yaml-diff-table th:nth-child(4) {
    width: 16%;
}


/* ============================================================
   CHANGED
   ============================================================ */

.diff-changed .key-cell {
    background: #fff1f2;
    color: #b42318;
    font-weight: 700;
}

.diff-changed .backup-cell {
    background: #ffe4e6;
    color: #b42318;
    font-weight: 600;
}

.diff-changed .current-cell {
    background: #dcfce7;
    color: #027a48;
    font-weight: 600;
}


/* ============================================================
   ADDED
   ============================================================ */

.diff-added .key-cell {
    background: #ecfdf3;
    color: #027a48;
    font-weight: 700;
}

.diff-added .backup-cell {
    background: #f8fafc;
    color: #667085;
}

.diff-added .current-cell {
    background: #dcfce7;
    color: #027a48;
    font-weight: 600;
}


/* ============================================================
   REMOVED
   ============================================================ */

.diff-removed .key-cell {
    background: #fff7ed;
    color: #c2410c;
    font-weight: 700;
}

.diff-removed .backup-cell {
    background: #ffedd5;
    color: #c2410c;
    font-weight: 600;
}

.diff-removed .current-cell {
    background: #f8fafc;
    color: #667085;
}


/* ============================================================
   STATUS BADGES
   ============================================================ */

.status-badge {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    white-space: nowrap;
}

.status-changed {
    background: #fee2e2;
    color: #b42318;
}

.status-added {
    background: #dcfce7;
    color: #027a48;
}

.status-removed {
    background: #ffedd5;
    color: #c2410c;
}


/* ============================================================
   NO DIFFERENCE
   ============================================================ */

.yaml-no-diff {
    padding: 18px;
    background: #ecfdf3;
    border: 1px solid #abefc6;
    color: #027a48;
    border-radius: 8px;
    margin-bottom: 20px;
    font-weight: 600;
}


/* ============================================================
   RESPONSIVE
   ============================================================ */

@media (max-width: 900px) {

    .yaml-summary-container {
        flex-direction: column;
    }

    .yaml-page-title-text {
        font-size: 30px;
    }

}

</style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# HTML HELPER
# ============================================================

def render_html(html_content):

    """
    IMPORTANT:
    st.html() prevents Streamlit from displaying
    HTML tags as plain text.
    """

    st.html(
        dedent(html_content)
    )


# ============================================================
# RESOURCE NAME
# ============================================================

def get_resource_name(resource):

    if not resource:
        return "Unknown Resource"

    metadata = resource.get(
        "metadata",
        {},
    ) or {}

    kind = resource.get(
        "kind",
        "Unknown",
    )

    namespace = metadata.get(
        "namespace",
        "default",
    )

    name = metadata.get(
        "name",
        "unknown",
    )

    return (
        f"{kind} / "
        f"{namespace} / "
        f"{name}"
    )


# ============================================================
# RESOURCE ID
# ============================================================

def get_resource_id(resource):

    metadata = resource.get(
        "metadata",
        {},
    ) or {}

    kind = str(
        resource.get(
            "kind",
            "",
        )
    ).strip().lower()

    namespace = str(
        metadata.get(
            "namespace",
            "default",
        )
    ).strip().lower()

    name = str(
        metadata.get(
            "name",
            "",
        )
    ).strip().lower()

    return (
        kind,
        namespace,
        name,
    )


# ============================================================
# READ YAML
# ============================================================

def load_yaml_documents(uploaded_files):

    resources = []

    if not uploaded_files:
        return resources

    for uploaded_file in uploaded_files:

        try:

            file_bytes = uploaded_file.getvalue()

            if len(file_bytes) > MAX_FILE_SIZE:

                st.error(
                    f"{uploaded_file.name} is larger "
                    f"than 200 MB."
                )

                continue

            content = file_bytes.decode(
                "utf-8",
                errors="replace",
            )

            documents = yaml.safe_load_all(
                content
            )

            for document in documents:

                if not document:
                    continue

                # ------------------------------------------------
                # Kubernetes List
                # ------------------------------------------------

                if (
                    isinstance(document, dict)
                    and document.get("kind")
                    and str(
                        document.get("kind")
                    ).endswith("List")
                ):

                    items = document.get(
                        "items",
                        [],
                    )

                    for item in items:

                        if isinstance(
                            item,
                            dict,
                        ):

                            item[
                                "_source_file"
                            ] = uploaded_file.name

                            resources.append(
                                item
                            )

                    continue

                # ------------------------------------------------
                # List of objects
                # ------------------------------------------------

                if isinstance(
                    document,
                    list,
                ):

                    for item in document:

                        if isinstance(
                            item,
                            dict,
                        ):

                            item[
                                "_source_file"
                            ] = uploaded_file.name

                            resources.append(
                                item
                            )

                    continue

                # ------------------------------------------------
                # Normal Kubernetes object
                # ------------------------------------------------

                if isinstance(
                    document,
                    dict,
                ):

                    document[
                        "_source_file"
                    ] = uploaded_file.name

                    resources.append(
                        document
                    )

        except Exception as exc:

            st.error(
                f"Unable to read "
                f"{uploaded_file.name}: {exc}"
            )

    return resources


# ============================================================
# FILTER RESOURCE TYPES
# ============================================================

def filter_resources(
    resources,
    selected_types,
):

    return [
        resource
        for resource in resources
        if resource.get("kind")
        in selected_types
    ]


# ============================================================
# GET COMPARISON SECTION
# ============================================================

def get_comparison_data(resource):

    """
    ConfigMap:
        ONLY data

    Secret:
        ONLY data

    All other supported resources:
        ONLY spec

    Metadata is completely ignored.
    """

    kind = str(
        resource.get(
            "kind",
            "",
        )
    ).strip()

    # ========================================================
    # CONFIGMAP
    # ========================================================

    if kind == "ConfigMap":

        return resource.get(
            "data",
            {},
        ) or {}

    # ========================================================
    # SECRET
    # ========================================================

    if kind == "Secret":

        return resource.get(
            "data",
            {},
        ) or {}

    # ========================================================
    # ALL OTHER RESOURCES
    # ========================================================

    return resource.get(
        "spec",
        {},
    ) or {}


# ============================================================
# FLATTEN YAML
# ============================================================

def flatten_data(
    value,
    parent_key="",
):

    result = {}

    # ========================================================
    # DICTIONARY
    # ========================================================

    if isinstance(
        value,
        dict,
    ):

        if not value:

            if parent_key:
                result[parent_key] = {}

            return result

        for key, child in value.items():

            key = str(key)

            if parent_key:

                full_key = (
                    f"{parent_key}.{key}"
                )

            else:

                full_key = key

            result.update(
                flatten_data(
                    child,
                    full_key,
                )
            )

        return result

    # ========================================================
    # LIST
    # ========================================================

    if isinstance(
        value,
        list,
    ):

        if not value:

            result[parent_key] = []

            return result

        for index, child in enumerate(
            value
        ):

            full_key = (
                f"{parent_key}[{index}]"
            )

            result.update(
                flatten_data(
                    child,
                    full_key,
                )
            )

        return result

    # ========================================================
    # VALUE
    # ========================================================

    result[parent_key] = value

    return result


# ============================================================
# FORMAT VALUE
# ============================================================

def format_value(value):

    if value is None:

        return "null"

    if isinstance(
        value,
        bool,
    ):

        return (
            "true"
            if value
            else "false"
        )

    if isinstance(
        value,
        (dict, list),
    ):

        try:

            return yaml.safe_dump(
                value,
                default_flow_style=True,
                sort_keys=False,
                allow_unicode=True,
            ).strip()

        except Exception:

            return str(value)

    return str(value)


# ============================================================
# COMPARE TWO RESOURCES
# ============================================================

def compare_resource(
    backup_resource,
    current_resource,
):

    differences = []

    # ========================================================
    # RESOURCE ADDED
    # ========================================================

    if backup_resource is None:

        differences.append(
            {
                "key": "__RESOURCE__",
                "backup": "Missing",
                "current": get_resource_name(
                    current_resource
                ),
                "status": "ADDED",
            }
        )

        return differences

    # ========================================================
    # RESOURCE REMOVED
    # ========================================================

    if current_resource is None:

        differences.append(
            {
                "key": "__RESOURCE__",
                "backup": get_resource_name(
                    backup_resource
                ),
                "current": "Missing",
                "status": "REMOVED",
            }
        )

        return differences

    # ========================================================
    # GET ONLY DATA/SPEC
    # ========================================================

    backup_data = get_comparison_data(
        backup_resource
    )

    current_data = get_comparison_data(
        current_resource
    )

    # ========================================================
    # FLATTEN
    # ========================================================

    backup_flat = flatten_data(
        backup_data
    )

    current_flat = flatten_data(
        current_data
    )

    # ========================================================
    # ALL KEYS
    # ========================================================

    all_keys = sorted(
        set(backup_flat.keys())
        |
        set(current_flat.keys())
    )

    # ========================================================
    # COMPARE
    # ========================================================

    for key in all_keys:

        backup_exists = (
            key in backup_flat
        )

        current_exists = (
            key in current_flat
        )

        # ====================================================
        # BOTH EXIST
        # ====================================================

        if (
            backup_exists
            and current_exists
        ):

            backup_value = (
                backup_flat[key]
            )

            current_value = (
                current_flat[key]
            )

            # SAME
            if (
                backup_value
                == current_value
            ):
                continue

            # CHANGED
            differences.append(
                {
                    "key": key,
                    "backup": format_value(
                        backup_value
                    ),
                    "current": format_value(
                        current_value
                    ),
                    "status": "CHANGED",
                }
            )

            continue

        # ====================================================
        # CURRENT ONLY
        # ====================================================

        if current_exists:

            differences.append(
                {
                    "key": key,
                    "backup": "Missing",
                    "current": format_value(
                        current_flat[key]
                    ),
                    "status": "ADDED",
                }
            )

            continue

        # ====================================================
        # BACKUP ONLY
        # ====================================================

        if backup_exists:

            differences.append(
                {
                    "key": key,
                    "backup": format_value(
                        backup_flat[key]
                    ),
                    "current": "Missing",
                    "status": "REMOVED",
                }
            )

    return differences


# ============================================================
# RESOURCE MAP
# ============================================================

def create_resource_map(
    resources
):

    resource_map = {}

    for resource in resources:

        resource_id = get_resource_id(
            resource
        )

        resource_map[
            resource_id
        ] = resource

    return resource_map


# ============================================================
# SAFE HTML
# ============================================================

def safe_html(value):

    return escape(
        str(value)
    ).replace(
        "\n",
        "<br>",
    )


# ============================================================
# RENDER RESOURCE TABLE
# ============================================================

def render_resource_table(
    resource_name,
    differences,
):

    # ========================================================
    # NO DIFFERENCES
    # ========================================================

    if not differences:

        render_html(
            f"""
            <div class="resource-header">
                {escape(resource_name)}
            </div>

            <div class="yaml-no-diff">
                ✅ No differences found.
            </div>
            """
        )

        return

    # ========================================================
    # RESOURCE HEADER
    # ========================================================

    render_html(
        f"""
        <div class="resource-header">
            🔎 {escape(resource_name)}
        </div>
        """
    )

    rows = []

    # ========================================================
    # ROWS
    # ========================================================

    for diff in differences:

        key = diff["key"]

        backup = diff["backup"]

        current = diff["current"]

        status = diff["status"]

        # ----------------------------------------------------
        # CHANGED
        # ----------------------------------------------------

        if status == "CHANGED":

            row_class = "diff-changed"

            badge = (
                '<span class="status-badge '
                'status-changed">'
                'CHANGED'
                '</span>'
            )

        # ----------------------------------------------------
        # ADDED
        # ----------------------------------------------------

        elif status == "ADDED":

            row_class = "diff-added"

            badge = (
                '<span class="status-badge '
                'status-added">'
                'ADDED'
                '</span>'
            )

        # ----------------------------------------------------
        # REMOVED
        # ----------------------------------------------------

        else:

            row_class = "diff-removed"

            badge = (
                '<span class="status-badge '
                'status-removed">'
                'REMOVED'
                '</span>'
            )

        rows.append(
            f"""
            <tr class="{row_class}">

                <td class="key-cell">
                    {safe_html(key)}
                </td>

                <td class="backup-cell">
                    {safe_html(backup)}
                </td>

                <td class="current-cell">
                    {safe_html(current)}
                </td>

                <td>
                    {badge}
                </td>

            </tr>
            """
        )

    # ========================================================
    # TABLE
    # ========================================================

    render_html(
        f"""
        <div class="yaml-diff-wrapper">

            <table class="yaml-diff-table">

                <thead>

                    <tr>

                        <th>
                            YAML KEY
                        </th>

                        <th>
                            BACKUP YAML
                        </th>

                        <th>
                            CURRENT YAML
                        </th>

                        <th>
                            STATUS
                        </th>

                    </tr>

                </thead>

                <tbody>
                    {"".join(rows)}
                </tbody>

            </table>

        </div>
        """
    )


# ============================================================
# SUMMARY
# ============================================================

def render_summary(
    all_differences,
):

    changed = 0
    added = 0
    removed = 0

    for diff in all_differences:

        if diff["status"] == "CHANGED":
            changed += 1

        elif diff["status"] == "ADDED":
            added += 1

        elif diff["status"] == "REMOVED":
            removed += 1

    total = (
        changed
        + added
        + removed
    )

    render_html(
        f"""
        <div class="yaml-summary-container">

            <div class="yaml-summary-card">

                <div class="yaml-summary-label">
                    Total Differences
                </div>

                <div class="yaml-summary-number">
                    {total}
                </div>

            </div>

            <div class="yaml-summary-card">

                <div class="yaml-summary-label">
                    Changed
                </div>

                <div class="yaml-summary-number">
                    {changed}
                </div>

            </div>

            <div class="yaml-summary-card">

                <div class="yaml-summary-label">
                    Added
                </div>

                <div class="yaml-summary-number">
                    {added}
                </div>

            </div>

            <div class="yaml-summary-card">

                <div class="yaml-summary-label">
                    Removed
                </div>

                <div class="yaml-summary-number">
                    {removed}
                </div>

            </div>

        </div>
        """
    )


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_yaml_comparator():

    load_css()

    # ========================================================
    # TITLE
    # ========================================================

    render_html(
        """
        <div class="yaml-page-title">

            <span class="yaml-page-icon">
                📄
            </span>

            <span class="yaml-page-title-text">
                YAML Comparator
            </span>

        </div>

        <div class="yaml-page-subtitle">
            Compare Kubernetes backup YAML against
            the current YAML configuration.
        </div>
        """
    )

    # ========================================================
    # RESOURCE TYPES
    # ========================================================

    render_html(
        """
        <div class="yaml-section-title">
            🔎 Resource Types
        </div>
        """
    )

    selected_types = st.multiselect(
        "Select resource types to compare",
        RESOURCE_TYPES,
        default=[
            "Deployment",
            "ConfigMap",
            "Secret",
        ],
        key="yaml_resource_types",
    )

    if selected_types:

        st.caption(
            "Selected: "
            + ", ".join(
                selected_types
            )
        )

    # ========================================================
    # COMPARISON INFORMATION
    # ========================================================

    render_html(
        """
        <div class="yaml-info-box">

            <div class="yaml-info-title">
                Comparison Mode
            </div>

            <div class="yaml-info-text">

                <b>ConfigMap:</b>
                compare only <code>data:</code>
                key/value pairs.

                <br><br>

                <b>Secret:</b>
                compare only <code>data:</code>
                key/value pairs.

                <br><br>

                <b>Deployment / StatefulSet / DaemonSet /
                Job / CronJob / Service / Ingress /
                PersistentVolumeClaim:</b>
                compare only <code>spec:</code>.

                <br><br>

                Kubernetes metadata such as
                annotations, labels,
                creationTimestamp,
                resourceVersion, uid,
                managedFields and Helm metadata
                are ignored.

            </div>

        </div>
        """
    )

    # ========================================================
    # UPLOADS
    # ========================================================

    backup_col, current_col = st.columns(
        2,
        gap="large",
    )

    # ========================================================
    # BACKUP
    # ========================================================

    with backup_col:

        render_html(
            """
            <div class="yaml-upload-title">
                📦 Backup YAML
            </div>

            <div class="yaml-upload-subtitle">
                Upload the backup Kubernetes YAML file(s).
            </div>
            """
        )

        backup_files = st.file_uploader(
            "Upload backup YAML file(s)",
            type=[
                "yaml",
                "yml",
            ],
            accept_multiple_files=True,
            key="yaml_backup_upload",
        )

    # ========================================================
    # CURRENT
    # ========================================================

    with current_col:

        render_html(
            """
            <div class="yaml-upload-title">
                🔄 Current YAML
            </div>

            <div class="yaml-upload-subtitle">
                Upload the current Kubernetes YAML file(s).
            </div>
            """
        )

        current_files = st.file_uploader(
            "Upload current YAML file(s)",
            type=[
                "yaml",
                "yml",
            ],
            accept_multiple_files=True,
            key="yaml_current_upload",
        )

    # ========================================================
    # FILE INFORMATION
    # ========================================================

    if backup_files:

        render_html(
            f"""
            <div class="yaml-file-status">
                📦 Backup YAML loaded:
                <b>{len(backup_files)}</b> file(s)
            </div>
            """
        )

    if current_files:

        render_html(
            f"""
            <div class="yaml-file-status">
                🔄 Current YAML loaded:
                <b>{len(current_files)}</b> file(s)
            </div>
            """
        )

    # ========================================================
    # COMPARE BUTTON
    # ========================================================

    compare_clicked = st.button(
        "🔎  Compare YAML",
        type="primary",
        use_container_width=True,
        key="compare_yaml_button",
    )

    if not compare_clicked:

        return

    # ========================================================
    # VALIDATION
    # ========================================================

    if not selected_types:

        st.error(
            "Please select at least one resource type."
        )

        return

    if not backup_files:

        st.error(
            "Please upload Backup YAML."
        )

        return

    if not current_files:

        st.error(
            "Please upload Current YAML."
        )

        return

    # ========================================================
    # READ FILES
    # ========================================================

    with st.spinner(
        "Reading YAML files..."
    ):

        backup_resources = (
            load_yaml_documents(
                backup_files
            )
        )

        current_resources = (
            load_yaml_documents(
                current_files
            )
        )

    # ========================================================
    # FILTER
    # ========================================================

    backup_resources = filter_resources(
        backup_resources,
        selected_types,
    )

    current_resources = filter_resources(
        current_resources,
        selected_types,
    )

    # ========================================================
    # MAP
    # ========================================================

    backup_map = create_resource_map(
        backup_resources
    )

    current_map = create_resource_map(
        current_resources
    )

    # ========================================================
    # RESOURCE IDS
    # ========================================================

    resource_ids = sorted(
        set(backup_map.keys())
        |
        set(current_map.keys())
    )

    # ========================================================
    # COMPARE
    # ========================================================

    results = []

    all_differences = []

    for resource_id in resource_ids:

        backup_resource = backup_map.get(
            resource_id
        )

        current_resource = current_map.get(
            resource_id
        )

        resource = (
            backup_resource
            if backup_resource is not None
            else current_resource
        )

        resource_name = (
            get_resource_name(
                resource
            )
        )

        differences = compare_resource(
            backup_resource,
            current_resource,
        )

        results.append(
            (
                resource_name,
                differences,
            )
        )

        all_differences.extend(
            differences
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    render_summary(
        all_differences
    )

    # ========================================================
    # RESULTS TITLE
    # ========================================================

    render_html(
        """
        <div class="yaml-section-title">
            🔎 Resource Differences
        </div>
        """
    )

    # ========================================================
    # ONLY DIFFERENCES
    # ========================================================

    differences_found = False

    for (
        resource_name,
        differences,
    ) in results:

        if not differences:
            continue

        differences_found = True

        render_resource_table(
            resource_name,
            differences,
        )

    # ========================================================
    # NO DIFFERENCE
    # ========================================================

    if not differences_found:

        render_html(
            """
            <div class="yaml-no-diff">
                ✅ No differences found.
                Backup YAML and Current YAML
                are identical for the selected
                resource types.
            </div>
            """
        )


# ============================================================
# ALIAS
# ============================================================

def render_yaml_comparator_page():

    render_yaml_comparator()


# ============================================================
# DIRECT RUN
# ============================================================

if __name__ == "__main__":

    configure_page()

    render_yaml_comparator()