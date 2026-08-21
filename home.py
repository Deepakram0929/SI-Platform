import streamlit as st


def render_home():
    """SI-PLATFORM home page.

    Only the home-page presentation is defined here.
    Existing sidebar, routing and other modules remain unchanged.
    """

    # ============================================================
    # HOME PAGE STYLES
    # ============================================================

    st.markdown(
        """
        <style>
        /* =========================================================
           USE THE AVAILABLE SCREEN WIDTH
           ========================================================= */

        .block-container {
            max-width: 100% !important;
            padding-top: 1.5rem !important;
            padding-left: 2.2rem !important;
            padding-right: 2.2rem !important;
            padding-bottom: 2rem !important;
        }

        .si-home {
            width: 100%;
            padding: 0 0 40px 0;
        }

        /* =========================================================
           HEADER
           ========================================================= */

        .si-pill {
            display: inline-block;
            padding: 7px 16px;
            border-radius: 999px;
            background: #eef5ff;
            border: 1px solid #d8e6ff;
            color: #075bd8;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 1.1px;
        }

        .si-title {
            margin-top: 7px;
            color: #10255d;
            font-size: 46px;
            line-height: 1.05;
            font-weight: 850;
            text-align: center;
            letter-spacing: -1.5px;
        }

        .si-subtitle {
            margin-top: 8px;
            color: #1167e8;
            font-size: 22px;
            line-height: 1.25;
            font-weight: 750;
            text-align: center;
        }

        .si-description {
            max-width: 900px;
            margin: 8px auto 0 auto;
            color: #66758f;
            font-size: 15px;
            line-height: 1.6;
            text-align: center;
        }

        /* =========================================================
           HERO VISUAL
           ========================================================= */

        .si-hero-wrap {
            width: 100%;
            display: flex;
            justify-content: center;
        }

        .si-hero-card {
            position: relative;
            width: 100%;
            max-width: 1250px;
            height: 350px;
            margin: 20px auto 28px auto;
            overflow: hidden;
            border: 1px solid #dbe7f7;
            border-radius: 24px;
            background:
                radial-gradient(
                    circle at 50% 48%,
                    rgba(47, 125, 255, 0.15) 0,
                    rgba(47, 125, 255, 0.07) 145px,
                    rgba(47, 125, 255, 0) 310px
                ),
                linear-gradient(
                    135deg,
                    #ffffff 0%,
                    #f7faff 52%,
                    #f2f7ff 100%
                );
            box-shadow:
                0 18px 45px rgba(35, 83, 145, 0.09),
                inset 0 1px 0 rgba(255,255,255,0.95);
        }

        .si-hero-card::before {
            content: "";
            position: absolute;
            inset: 0;
            background-image:
                radial-gradient(
                    circle,
                    rgba(48, 116, 232, 0.16) 1px,
                    transparent 1.5px
                );
            background-size: 34px 34px;
            opacity: 0.28;
        }

        .si-hero-label {
            position: absolute;
            left: 50%;
            top: 20px;
            transform: translateX(-50%);
            color: #6580a6;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 2px;
            z-index: 10;
            white-space: nowrap;
        }

        /* =========================================================
           CONNECTION LINES
           ========================================================= */

        .si-connect {
            position: absolute;
            left: 50%;
            top: 50%;
            width: 330px;
            height: 1px;
            transform-origin: left center;
            background:
                linear-gradient(
                    90deg,
                    rgba(40, 121, 242, 0.78),
                    rgba(40, 121, 242, 0.08)
                );
            z-index: 2;
        }

        .si-connect::after {
            content: "";
            position: absolute;
            right: 0;
            top: -3px;
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #2f80ed;
            box-shadow: 0 0 10px rgba(47,128,237,.55);
        }

        .c1 { transform: rotate(205deg); }
        .c2 { transform: rotate(180deg); }
        .c3 { transform: rotate(155deg); }
        .c4 { transform: rotate(-25deg); }
        .c5 { transform: rotate(0deg); }
        .c6 { transform: rotate(25deg); }

        /* =========================================================
           CENTRAL 3D PLATFORM
           ========================================================= */

        .si-core-glow {
            position: absolute;
            left: 50%;
            top: 49%;
            width: 330px;
            height: 220px;
            transform: translate(-50%, -50%);
            border-radius: 50%;
            background:
                radial-gradient(
                    ellipse,
                    rgba(44, 123, 245, 0.22) 0%,
                    rgba(44, 123, 245, 0.08) 45%,
                    rgba(44, 123, 245, 0) 72%
                );
            filter: blur(8px);
            z-index: 1;
        }

        .si-base-bottom {
            position: absolute;
            left: 50%;
            top: 61%;
            width: 270px;
            height: 82px;
            transform: translate(-50%, -50%);
            border-radius: 50%;
            background:
                linear-gradient(
                    180deg,
                    #d9e9ff 0%,
                    #75a9fa 38%,
                    #1169e8 100%
                );
            box-shadow:
                0 20px 35px rgba(26, 98, 216, 0.25),
                0 0 30px rgba(45, 126, 245, 0.17);
            z-index: 3;
        }

        .si-base-top {
            position: absolute;
            left: 50%;
            top: 56%;
            width: 235px;
            height: 72px;
            transform: translate(-50%, -50%);
            border-radius: 50%;
            background:
                linear-gradient(
                    180deg,
                    #ffffff 0%,
                    #e7f0ff 100%
                );
            box-shadow:
                0 8px 18px rgba(34, 82, 143, 0.15);
            z-index: 4;
        }

        .si-core {
            position: absolute;
            left: 50%;
            top: 42%;
            width: 128px;
            height: 128px;
            transform: translate(-50%, -50%) rotate(45deg);
            border-radius: 27px;
            background:
                linear-gradient(
                    145deg,
                    #5aa3ff 0%,
                    #1670ef 52%,
                    #073a99 100%
                );
            border: 1px solid rgba(255,255,255,.42);
            box-shadow:
                0 22px 35px rgba(19, 88, 205, .32),
                inset 2px 2px 5px rgba(255,255,255,.35),
                inset -5px -8px 14px rgba(0,42,125,.18);
            z-index: 7;
        }

        .si-core-inner {
            position: absolute;
            left: 50%;
            top: 50%;
            width: 88px;
            height: 88px;
            transform: translate(-50%, -50%) rotate(-45deg);
            border-radius: 21px;
            border: 2px solid rgba(255,255,255,.52);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            font-size: 42px;
            text-shadow: 0 3px 8px rgba(0,0,0,.20);
        }

        .si-core-name {
            position: absolute;
            left: 50%;
            top: 76%;
            transform: translateX(-50%);
            color: #1167e8;
            font-size: 13px;
            font-weight: 850;
            letter-spacing: 1.2px;
            white-space: nowrap;
            z-index: 9;
        }

        /* =========================================================
           FLOATING CAPABILITY CHIPS
           ========================================================= */

        .si-chip {
            position: absolute;
            min-width: 118px;
            padding: 11px 17px;
            border: 1px solid #d8e5f7;
            border-radius: 17px;
            background: rgba(255,255,255,.97);
            box-shadow:
                0 10px 24px rgba(35, 82, 140, .12),
                0 2px 6px rgba(35, 82, 140, .06);
            color: #173a70;
            text-align: center;
            font-size: 11px;
            font-weight: 850;
            letter-spacing: .65px;
            z-index: 12;
        }

        .si-chip::before {
            content: "";
            display: inline-block;
            width: 6px;
            height: 6px;
            margin-right: 7px;
            border-radius: 50%;
            background: #2d7ff0;
            box-shadow: 0 0 9px rgba(45,127,240,.65);
            vertical-align: middle;
        }

        .si-validate {
            left: 8%;
            top: 19%;
        }

        .si-automate {
            left: 3%;
            top: 49%;
        }

        .si-operate {
            left: 14%;
            bottom: 12%;
        }

        .si-compare {
            right: 8%;
            top: 19%;
        }

        .si-backup {
            right: 3%;
            top: 49%;
        }

        .si-report {
            right: 14%;
            bottom: 12%;
        }

        /* =========================================================
           WHAT YOU CAN DO
           ========================================================= */

        .si-section-title {
            width: 100%;
            max-width: 1250px;
            margin: 0 auto 12px auto;
            color: #13265b;
            font-size: 26px;
            font-weight: 800;
        }

        .si-card {
            min-height: 205px;
            padding: 20px 18px 16px 18px;
            border: 1px solid #dce5f2;
            border-radius: 15px;
            background:
                linear-gradient(
                    180deg,
                    #ffffff 0%,
                    #fbfdff 100%
                );
            box-shadow:
                0 5px 20px rgba(31, 72, 130, .06);
        }

        .si-card-icon {
            width: 44px;
            height: 44px;
            margin-bottom: 12px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #edf5ff;
            color: #0d63df;
        }

        .si-card-icon svg {
            width: 23px;
            height: 23px;
            stroke: #0d63df;
            fill: none;
            stroke-width: 1.8;
            stroke-linecap: round;
            stroke-linejoin: round;
        }

        .si-card-title {
            min-height: 42px;
            margin-bottom: 8px;
            color: #17345f;
            font-size: 16px;
            font-weight: 750;
            line-height: 1.3;
        }

        .si-card-text {
            min-height: 61px;
            color: #667085;
            font-size: 13px;
            line-height: 1.55;
        }

        .si-card-link {
            margin-top: 14px;
            color: #0865df;
            font-size: 13px;
            font-weight: 700;
        }

        /* =========================================================
           RESPONSIVE
           ========================================================= */

        @media (min-width: 1400px) {
            .si-hero-card {
                max-width: 1350px;
                height: 360px;
            }

            .si-section-title {
                max-width: 1350px;
            }
        }

        @media (max-width: 1200px) {
            .si-hero-card {
                max-width: 100%;
                height: 340px;
            }

            .si-connect {
                width: 270px;
            }
        }

        @media (max-width: 900px) {
            .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }

            .si-home {
                padding-left: 0;
                padding-right: 0;
            }

            .si-hero-card {
                height: 320px;
                border-radius: 18px;
            }

            .si-title {
                font-size: 38px;
            }

            .si-subtitle {
                font-size: 20px;
            }

            .si-chip {
                min-width: 90px;
                padding: 8px 9px;
                font-size: 9px;
            }
        }

        @media (max-width: 600px) {
            .si-title {
                font-size: 32px;
            }

            .si-subtitle {
                font-size: 17px;
            }

            .si-description {
                font-size: 13px;
            }

            .si-hero-card {
                height: 300px;
            }

            .si-core {
                width: 100px;
                height: 100px;
            }

            .si-core-inner {
                width: 70px;
                height: 70px;
                font-size: 32px;
            }

            .si-base-bottom {
                width: 200px;
            }

            .si-base-top {
                width: 175px;
            }

            .si-chip {
                min-width: 75px;
                padding: 7px 6px;
                font-size: 8px;
            }

            .si-chip::before {
                display: none;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="si-home">',
        unsafe_allow_html=True,
    )

    # ============================================================
    # HEADER
    # ============================================================

    st.markdown(
        """
        <div style="text-align:center;">
            <span class="si-pill">
                KUBERNETES AUTOMATION PLATFORM
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="si-title">SI-PLATFORM</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="si-subtitle">
            Kubernetes Automation &amp; Validation Suite
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="si-description">
            Automate, validate, compare and operate your Kubernetes
            environments with confidence.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ============================================================
    # HERO
    # Pure HTML/CSS. No image file required.
    # ============================================================

    hero_html = """
    <div class="si-hero-wrap">
        <div class="si-hero-card">

            <div class="si-hero-label">
                AUTOMATE • VALIDATE • COMPARE • OPERATE
            </div>

            <div class="si-core-glow"></div>

            <!-- Connection lines -->
            <div class="si-connect c1"></div>
            <div class="si-connect c2"></div>
            <div class="si-connect c3"></div>
            <div class="si-connect c4"></div>
            <div class="si-connect c5"></div>
            <div class="si-connect c6"></div>

            <!-- 3D platform -->
            <div class="si-base-bottom"></div>
            <div class="si-base-top"></div>

            <div class="si-core">
                <div class="si-core-inner">⚙</div>
            </div>

            <div class="si-core-name">
                SI-PLATFORM
            </div>

            <!-- Capabilities -->
            <div class="si-chip si-validate">VALIDATE</div>
            <div class="si-chip si-automate">AUTOMATE</div>
            <div class="si-chip si-operate">OPERATE</div>

            <div class="si-chip si-compare">COMPARE</div>
            <div class="si-chip si-backup">BACKUP</div>
            <div class="si-chip si-report">REPORT</div>

        </div>
    </div>
    """

    if hasattr(st, "html"):
        st.html(hero_html)
    else:
        st.markdown(hero_html, unsafe_allow_html=True)

    # ============================================================
    # WHAT YOU CAN DO
    # ============================================================

    st.markdown(
        '<div class="si-section-title">What you can do</div>',
        unsafe_allow_html=True,
    )

    # Professional inline SVG icons.
    cards = [
        (
            "DB String",
            "Validate and manage database connection strings and connectivity configuration.",
            "db",
            "DB String",
            "home_db",
        ),
        (
            "Cluster Comparison Report",
            "Generate detailed comparison reports for Kubernetes cluster resources and configuration.",
            "report",
            "Cluster Comparison Report",
            "home_report",
        ),
        (
            "Ingress",
            "Validate ingress endpoints, connectivity and routing across Kubernetes environments.",
            "network",
            "Ingress",
            "home_ingress",
        ),
        (
            "Namespace Backup",
            "Create and manage namespace-level backups before making Kubernetes configuration changes.",
            "backup",
            "Namespace Backup",
            "home_backup",
        ),
        (
            "Environment Comparator",
            "Compare Kubernetes resources across two environments and identify configuration differences.",
            "compare",
            "Environment Comparator",
            "home_environment",
        ),
    ]

    icons = {
        "db": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <ellipse cx="12" cy="5" rx="7" ry="3"></ellipse>
                <path d="M5 5v7c0 1.7 3.1 3 7 3s7-1.3 7-3V5"></path>
                <path d="M5 12v7c0 1.7 3.1 3 7 3s7-1.3 7-3v-7"></path>
                <path d="M9 10h.01"></path>
                <path d="M9 17h.01"></path>
            </svg>
        """,
        "report": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 3h10l4 4v14H5z"></path>
                <path d="M15 3v5h4"></path>
                <path d="M8 17v-4"></path>
                <path d="M12 17v-7"></path>
                <path d="M16 17v-2"></path>
            </svg>
        """,
        "network": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="12" cy="12" r="8"></circle>
                <path d="M4 12h16"></path>
                <path d="M12 4c2.2 2.2 3.4 4.8 3.4 8S14.2 17.8 12 20"></path>
                <path d="M12 4c-2.2 2.2-3.4 4.8-3.4 8S9.8 17.8 12 20"></path>
                <circle cx="19" cy="5" r="2"></circle>
                <path d="M17.6 6.4 15.8 8.2"></path>
            </svg>
        """,
        "backup": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <ellipse cx="12" cy="5" rx="7" ry="3"></ellipse>
                <path d="M5 5v6c0 1.7 3.1 3 7 3s7-1.3 7-3V5"></path>
                <path d="M5 11v6c0 1.7 3.1 3 7 3 1.2 0 2.3-.1 3.3-.4"></path>
                <path d="M17 15v6"></path>
                <path d="M14 18h6"></path>
            </svg>
        """,
        "compare": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <rect x="3" y="5" width="7" height="14" rx="1.5"></rect>
                <rect x="14" y="5" width="7" height="14" rx="1.5"></rect>
                <path d="M10 9h4"></path>
                <path d="m12 7 2 2-2 2"></path>
                <path d="M14 15h-4"></path>
                <path d="m12 13-2 2 2 2"></path>
            </svg>
        """,
    }

    columns = st.columns(5, gap="medium")

    for column, (
        title,
        description,
        icon_key,
        page,
        key,
    ) in zip(columns, cards):

        with column:

            card_html = f"""
            <div class="si-card">

                <div class="si-card-icon">
                    {icons[icon_key]}
                </div>

                <div class="si-card-title">
                    {title}
                </div>

                <div class="si-card-text">
                    {description}
                </div>

                <div class="si-card-link">
                    Open module →
                </div>

            </div>
            """

            if hasattr(st, "html"):
                st.html(card_html)
            else:
                st.markdown(
                    card_html,
                    unsafe_allow_html=True,
                )

            if st.button(
                f"Open {title} →",
                key=key,
                use_container_width=True,
            ):
                st.session_state.page = page
                st.rerun()

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )