import streamlit as st
import plotly.graph_objects as go
import numpy as np
import math

# 컨테이너 정보 (단위: mm)
CONTAINERS = {
    "20ft": {"length": 5898, "width": 2352, "height": 2395},
    "40ft": {"length": 12021, "width": 2352, "height": 2395},
    "40ft HC": {"length": 12021, "width": 2352, "height": 2691},
}

def calculate_cartons(per_carton, order_qty):
    return math.ceil(order_qty / per_carton)

def add_box(fig, x0, y0, z0, dx, dy, dz, color, name):
    # 박스를 구성하는 면 추가
    fig.add_trace(go.Mesh3d(
        x=[x0, x0+dx, x0+dx, x0, x0, x0+dx, x0+dx, x0],
        y=[y0, y0, y0+dy, y0+dy, y0, y0, y0+dy, y0+dy],
        z=[z0, z0, z0, z0, z0+dz, z0+dz, z0+dz, z0+dz],
        color=color,
        opacity=0.7,
        name=name
    ))

def draw_container(container_dim, boxes, container_type):
    fig = go.Figure()

    # 컨테이너 치수 및 CBM 계산
    cx, cy, cz = container_dim['length'], container_dim['width'], container_dim['height']
    container_cbm = (cx / 1000) * (cy / 1000) * (cz / 1000)

    # 컨테이너 그리기 (투명한 회색 박스)
    add_box(fig, 0, 0, 0, cx, cy, cz, 'lightgrey', 'Container')

    # 박스 배치 초기 위치
    current_x, current_y, current_z = 0, 0, 0
    used_cbm = 0
    total_loaded_boxes = 0
    colors = ['blue', 'red', 'green', 'orange', 'purple']
    color_idx = 0

    product_report = []

    for i, (bx, by, bz, qty, per_carton, name) in enumerate(boxes):
        box_count = 0
        for _ in range(qty):
            # 공간 초과 시 다음 행으로 이동
            if current_x + bx > cx:
                current_x = 0
                current_y += by

            # 공간 초과 시 다음 층으로 이동
            if current_y + by > cy:
                current_y = 0
                current_z += bz

            # 공간 초과 시 더 이상 배치 불가
            if current_z + bz > cz:
                st.warning(f"⚠️ 컨테이너에 더 이상 {name} 제품을 배치할 공간이 없습니다.")
                break

            # 박스 그리기
            add_box(fig, current_x, current_y, current_z, bx, by, bz, colors[color_idx % len(colors)], name)
            used_cbm += (bx * by * bz) / 1e9  # mm³을 m³으로 변환
            total_loaded_boxes += 1
            box_count += 1

            # 다음 박스의 x 좌표 업데이트
            current_x += bx

        # 제품별 CBM 및 전체 제품 수 계산
        product_cbm = (bx * by * bz * box_count) / 1e9
        total_products = per_carton * box_count
        product_report.append({
            "제품명": name,
            "선적된 박스 수": box_count,
            "전체 제품 수": total_products,
            "제품별 CBM": f"{product_cbm:.2f} m³"
        })

        color_idx += 1

    # 레이아웃 설정
    fig.update_layout(
        scene=dict(
            xaxis_title='Length (mm)',
            yaxis_title='Width (mm)',
            zaxis_title='Height (mm)',
            aspectmode='data'
        ),
        margin=dict(r=10, l=10, b=10, t=50),
        title="컨테이너 선적 시뮬레이션"
    )

    st.plotly_chart(fig, use_container_width=True)

    # 결과 요약 출력
    st.subheader("선적 정보 요약")
    total_cbm_used = sum(float(report["제품별 CBM"].split()[0]) for report in product_report)
    remaining_cbm = container_cbm - total_cbm_used
    st.write(f"**사용된 CBM:** {total_cbm_used:.2f} m³")
    st.write(f"**남은 CBM:** {remaining_cbm:.2f} m³")

    st.table(product_report)

# Streamlit UI 설정
st.set_page_config(page_title="혼적 컨테이너 선적 시뮬레이션", layout="wide")
st.title("혼적 컨테이너 선적 시뮬레이션 (고급 3D)")

# 사이드바 옵션창 생성
with st.sidebar:
    st.header("옵션 창")

    # 컨테이너 선택
    container_type = st.selectbox("컨테이너 사이즈 선택", list(CONTAINERS.keys()))
    container_dim = CONTAINERS[container_type]

    # 제품 수량 선택
    num_products = st.number_input("선적할 제품 종류 수", min_value=1, max_value=5, step=1)

    products = []
    for i in range(int(num_products)):
        with st.expander(f"제품 {i + 1} 설정", expanded=True):
            name = st.text_input(f"제품 {i + 1} 이름", f"Product {i + 1}")
            length = st.number_input(f"제품 {i + 1} 길이 (mm)", min_value=1, key=f'length_{i}')
            width = st.number_input(f"제품 {i + 1} 너비 (mm)", min_value=1, key=f'width_{i}')
            height = st.number_input(f"제품 {i + 1} 높이 (mm)", min_value=1, key=f'height_{i}')
            per_carton = st.number_input(f"제품 {i + 1} 카톤당 수량", min_value=1, key=f'per_carton_{i}')
            order_qty = st.number_input(f"제품 {i + 1} 발주 수량", min_value=1, key=f'order_qty_{i}')
            cartons = calculate_cartons(per_carton, order_qty)
            st.write(f"**총 카톤 수:** {cartons}")
            products.append((length, width, height, cartons, per_carton, name))

# 시뮬레이션 버튼
if st.button("시뮬레이션 시작"):
    draw_container(container_dim, products, container_type)
