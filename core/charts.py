import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from auth import get_db_connection

sns.set_theme(style="whitegrid")

COLORS = {
    'teal': '#2DD4BF', 'red': '#FF6B6B', 'blue': '#4DA6FF',
    'purple': '#A855F7', 'orange': '#F5A623', 'dark_red': '#E05C3A',
}
RISK_COLORS = {'Critical': '#E05C3A', 'Moderate': '#F5A623', 'Stable': '#2DD4BF'}


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_data(doctor_name=None):
    """
    Load patient data from DB.
    - doctor_name=None  → all patients (Admin view)
    - doctor_name=str   → only that doctor's patients (Doctor view)
    """
    conn = get_db_connection()
    if doctor_name:
        df = pd.read_sql("""
            SELECT p.*
            FROM Patients p
            JOIN Users u ON u.Username = p.Patient_name
            WHERE u.Doctor_name = ?
        """, conn, params=(doctor_name,))
    else:
        df = pd.read_sql("SELECT * FROM Patients", conn)
    conn.close()
    df.columns = df.columns.str.strip()
    return df


def styled_table(ax, rows, col_labels, title, row_colors=None):
    ax.axis('off')
    ax.figure.suptitle(title, fontsize=13, fontweight='bold')
    t = ax.table(cellText=rows, colLabels=col_labels, loc='center', cellLoc='center')
    t.set_fontsize(11)
    t.scale(1.5, 1.8)
    for col in range(len(col_labels)):
        t[0, col].set_facecolor(COLORS['blue'])
        t[0, col].set_text_props(color='white', fontweight='bold')
    if row_colors:
        for i, color in enumerate(row_colors):
            for col in range(len(col_labels)):
                t[i + 1, col].set_facecolor(color)
    else:
        for i in range(len(rows)):
            if (i + 1) % 2 == 0:
                for col in range(len(col_labels)):
                    t[i + 1, col].set_facecolor('#F5F8FF')


def bar_with_labels(ax, labels, values, colors, title, ylabel='Number of Patients'):
    for i, (label, value, color) in enumerate(zip(labels, values, colors)):
        ax.bar(label, value, color=color, width=0.5)
        ax.text(i, value + 0.3, str(value), ha='center', fontweight='bold', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_ylabel(ylabel)


# ── Shared Charts (used by both Admin and Doctor) ─────────────────────────────

def show_stats_table(df, title='Healthcare System Overview'):
    total = len(df)
    if total == 0:
        print("No patient data available.")
        return

    def pct(n): return f"{n} ({round(n / total * 100, 1)}%)"

    rows = [
        ['Total Patients',  str(total)],
        ['Diabetic',        pct((df['Diabetes_diagnosis'] == 'Yes').sum())],
        ['CVD',             pct((df['Cardiovascular_disease_diagnosis'] == 'Yes').sum())],
        ['Critical',        pct((df['Health_Risk'] == 'Critical').sum())],
        ['Moderate',        pct((df['Health_Risk'] == 'Moderate').sum())],
        ['Stable',          pct((df['Health_Risk'] == 'Stable').sum())],
        ['Avg Age',         f"{round(df['Age'].mean(), 1)} years"],
    ]
    fig, ax = plt.subplots(figsize=(8, 4))
    styled_table(ax, rows, ['Metric', 'Value'], title)
    plt.tight_layout()
    plt.show()


def show_disease_distribution(df, title='Disease Distribution Among Patients'):
    if len(df) == 0:
        return
    d = df['Diabetes_diagnosis'] == 'Yes'
    c = df['Cardiovascular_disease_diagnosis'] == 'Yes'
    labels = ['Diabetes Only', 'CVD Only', 'Both', 'Healthy']
    values = [(d & ~c).sum(), (~d & c).sum(), (d & c).sum(), (~d & ~c).sum()]
    colors = [COLORS['red'], COLORS['blue'], COLORS['purple'], COLORS['teal']]

    fig, ax = plt.subplots(figsize=(8, 5))
    bar_with_labels(ax, labels, values, colors, title)
    plt.tight_layout()
    plt.show()


def show_risk_distribution(df, title='Patient Risk Distribution'):
    if len(df) == 0:
        return
    risk_counts = df['Health_Risk'].value_counts()
    colors = [RISK_COLORS.get(r, 'gray') for r in risk_counts.index]
    plt.figure(figsize=(7, 7))
    plt.pie(risk_counts.values, labels=risk_counts.index, autopct='%1.1f%%',
            colors=colors, startangle=90, wedgeprops={'edgecolor': 'white', 'linewidth': 2})
    plt.title(title, fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.show()


def show_smoking_vs_cvd(df, title='Smoking Status vs Cardiovascular Disease'):
    if len(df) == 0:
        return
    plt.figure(figsize=(8, 5))
    sns.countplot(data=df, x='Smoking_status', hue='Cardiovascular_disease_diagnosis',
                  palette={'Yes': COLORS['red'], 'No': COLORS['teal']})
    plt.title(title, fontsize=14, fontweight='bold')
    plt.xlabel('Smoking Status')
    plt.ylabel('Number of Patients')
    plt.legend(title='CVD Diagnosis')
    plt.tight_layout()
    plt.show()


def show_age_by_risk(df, title='Age Group Distribution by Health Risk'):
    if len(df) == 0:
        return
    df = df.copy()
    df['Age Group'] = pd.cut(df['Age'], bins=[20, 30, 40, 50, 60, 70, 80],
                             labels=['20-30', '30-40', '40-50', '50-60', '60-70', '70-80'])
    grouped = df.groupby(['Age Group', 'Health_Risk'], observed=True).size().unstack(fill_value=0)
    cols = [c for c in ['Stable', 'Moderate', 'Critical'] if c in grouped.columns]
    grouped[cols].plot(kind='bar', figsize=(10, 6), color=[RISK_COLORS[c] for c in cols])
    plt.title(title, fontsize=14, fontweight='bold')
    plt.xlabel('Age Group')
    plt.ylabel('Number of Patients')
    plt.xticks(rotation=0)
    plt.legend(title='Health Risk')
    plt.tight_layout()
    plt.show()


# ── Admin-only Charts ─────────────────────────────────────────────────────────

def show_stress_analysis(df):
    """System-wide stress breakdown — Admin only."""
    if len(df) == 0:
        return
    plt.figure(figsize=(7, 5))
    ax = sns.countplot(data=df, x='Stress_level', order=['Low', 'Medium', 'High'],
                       palette={'Low': COLORS['teal'], 'Medium': COLORS['orange'], 'High': COLORS['dark_red']})
    for p in ax.patches:
        ax.text(p.get_x() + p.get_width() / 2, p.get_height() + 0.3,
                str(int(p.get_height())), ha='center', fontweight='bold', fontsize=12)
    plt.title('Stress Level Distribution (All Patients)', fontsize=14, fontweight='bold')
    plt.xlabel('Stress Level')
    plt.ylabel('Number of Patients')
    plt.tight_layout()
    plt.show()


def show_family_history(df):
    """Family history correlation — Admin only."""
    if len(df) == 0:
        return

    def history_counts(fam_col, diag_col):
        has_fam = df[fam_col] == 'Yes'
        got_disease = df[diag_col] == 'Yes'
        total = has_fam.sum()
        got = (has_fam & got_disease).sum()
        return total, got, total - got

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    specs = [
        ('Family_History_Diabetes',       'Diabetes_diagnosis',               'Diabetes', 'Got Diabetes', axes[0]),
        ('Family_history_Heart_disease',  'Cardiovascular_disease_diagnosis', 'CVD',      'Got CVD',      axes[1]),
    ]
    for fam_col, diag_col, disease_name, got_label, ax in specs:
        total, got, safe = history_counts(fam_col, diag_col)
        bar_with_labels(ax, [f'{got_label}\n({got})', f'Stayed Healthy\n({safe})'],
                        [got, safe], [COLORS['red'], COLORS['teal']],
                        f'{disease_name} Family History\n{total} had family history')
    plt.tight_layout()
    plt.show()


# ── Entry Points ──────────────────────────────────────────────────────────────

def show_admin_charts():
    """Full system-wide analytics for Admin."""
    df = load_data(doctor_name=None)
    show_stats_table(df, title='System-Wide Overview (All Patients)')
    show_disease_distribution(df, title='Disease Distribution — All Patients')
    show_risk_distribution(df, title='Risk Distribution — All Patients')
    show_smoking_vs_cvd(df, title='Smoking vs CVD — All Patients')
    show_age_by_risk(df, title='Age by Risk — All Patients')
    show_stress_analysis(df)       # Admin only
    show_family_history(df)        # Admin only


def show_doctor_charts(doctor_name):
    """
    Analytics scoped to this doctor's own patients only.
    No stress or family history charts — those need large populations to be meaningful.
    """
    df = load_data(doctor_name=doctor_name)
    if len(df) == 0:
        print(f"No patients found for Dr. {doctor_name}.")
        return
    show_stats_table(df,           title=f'My Patients Overview — Dr. {doctor_name}')
    show_disease_distribution(df,  title=f'Disease Distribution — Dr. {doctor_name}')
    show_risk_distribution(df,     title=f'Risk Distribution — Dr. {doctor_name}')
    show_smoking_vs_cvd(df,        title=f'Smoking vs CVD — Dr. {doctor_name}')
    show_age_by_risk(df,           title=f'Age by Risk — Dr. {doctor_name}')
    # Stress and Family History intentionally excluded for doctor view


# ── Main (CLI testing) ────────────────────────────────────────────────────────

if __name__ == "__main__":
    role = input("Enter role (admin/doctor): ").strip().lower()

    if role == 'admin':
        show_admin_charts()

    elif role == 'doctor':
        doctor_name = input("Enter doctor username: ").strip()
        show_doctor_charts(doctor_name)

    else:
        print("Invalid role. Patient charts have been removed from this module.")