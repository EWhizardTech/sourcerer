import streamlit as st


def apply_custom_styles():
    """Apply global custom CSS for the Streamlit app to look sleek."""
    st.markdown(
        """
        <style>
        .stButton > button {
            width: 100%;
            border-radius: 6px;
            font-weight: 600;
        }
        div[data-testid="stSidebarNav"] {
            padding-top: 1rem;
        }
        .main-header {
            font-size: 2.2rem;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 0;
            padding-bottom: 0;
        }
        .sub-header {
            font-size: 1.1rem;
            color: #6b7280;
            margin-top: 0;
            margin-bottom: 2rem;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        .status-ok {
            background-color: #dcfce7;
            color: #166534;
        }
        .status-error {
            background-color: #fee2e2;
            color: #991b1b;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str = ""):
    """Render a consistent header for pages."""
    st.markdown(f'<p class="main-header">{title}</p>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<p class="sub-header">{subtitle}</p>', unsafe_allow_html=True)
    st.divider()
