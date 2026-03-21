import { Swiper, SwiperSlide } from "swiper/react";
import { Navigation, Pagination, Autoplay, EffectCoverflow } from "swiper/modules";
import "swiper/css";
import "swiper/css/navigation";
import "swiper/css/pagination";
import "swiper/css/effect-coverflow";
import image1 from "../assects/image1.jpg.jpeg";
import image2 from "../assects/image2.jpg.jpeg";
import image3 from "../assects/image3.jpg.jpeg";
import image4 from "../assects/image4.jpg.jpeg";
import image5 from "../assects/image5.jpg.jpeg";
import image6 from "../assects/image6.jpg.jpeg";
import "../styles/imageSlider.css";

export default function ImageSlider() {
  const slides = [
    { src: image1, alt: "Slide 1" },
    { src: image2, alt: "Slide 2" },
    { src: image3, alt: "Slide 3" },
    { src: image4, alt: "Slide 4" },
    { src: image5, alt: "Slide 5" },
    { src: image6, alt: "Slide 6" }
  ];

  return (
    <div className="slider-container">
      <Swiper
        modules={[Navigation, Pagination, Autoplay, EffectCoverflow]}
        effect={"coverflow"}
        grabCursor={true}
        centeredSlides={true}
        slidesPerView={"auto"}
        coverflowEffect={{
          rotate: 0,
          stretch: 0,
          depth: 150,
          modifier: 1.5,
          slideShadows: true,
        }}
        spaceBetween={0}
        navigation={true}
        pagination={{
          clickable: true,
          dynamicBullets: true,
        }}
        autoplay={{
          delay: 3500,
          disableOnInteraction: false,
          pauseOnMouseEnter: true,
        }}
        loop={true}
        className="modern-slider"
      >
        {slides.map((slide, index) => (
          <SwiperSlide key={index} className="slider-slide">
            <img
              src={slide.src}
              alt={slide.alt}
              width="1200"
              height="460"
              loading={index === 0 ? "eager" : "lazy"}
              decoding={index === 0 ? "sync" : "async"}
              fetchPriority={index === 0 ? "high" : "auto"}
            />
          </SwiperSlide>
        ))}
      </Swiper>
    </div>
  );
}
