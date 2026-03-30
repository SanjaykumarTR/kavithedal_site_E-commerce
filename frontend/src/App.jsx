import { Routes, Route, Navigate } from "react-router-dom";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import Home from "./pages/Home";
import Login from "./pages/Login";
import VerifyOTP from "./pages/VerifyOTP";
import Books from "./pages/Books";
import About from "./pages/About";
import Contact from "./pages/Contact";
import Authors from "./pages/Authors";
import Blog from "./pages/Blog";
import WishlistPage from "./pages/WishlistPage";
import CartPage from "./pages/CartPage";
import Testimonials from "./pages/Testimonials";
import Contests from "./pages/Contests";
import ContestSubmission from "./pages/ContestSubmission";
import UserDashboard from "./pages/UserDashboard";
import BookDetail from "./pages/BookDetail";
import AuthorDetail from "./pages/AuthorDetail";
import Reader from "./pages/Reader";
import Library from "./pages/Library";
import EbookPurchase from "./pages/EbookPurchase";
import PurchaseSuccess from "./pages/PurchaseSuccess";
import PaymentFailure from "./pages/PaymentFailure";
import PhysicalPurchase from "./pages/PhysicalPurchase";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminLayout from "./components/admin/AdminLayout";
import AdminBooks from "./pages/admin/AdminBooks";
import AdminAuthors from "./pages/admin/AdminAuthors";
import AdminTestimonials from "./pages/admin/AdminTestimonials";
import AdminContests from "./pages/admin/AdminContests";
import AdminOrders from "./pages/admin/AdminOrders";
import ProtectedRoute from "./components/admin/ProtectedRoute";
import UserProtectedRoute from "./components/UserProtectedRoute";
import NotFound from "./pages/NotFound";

export default function App() {
  return (
    <>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<><Navbar /><Home /><Footer /></>} />
        <Route path="/books" element={<><Navbar /><Books /><Footer /></>} />
        <Route path="/authors" element={<><Navbar /><Authors /><Footer /></>} />
        <Route path="/author/:id" element={<><Navbar /><AuthorDetail /><Footer /></>} />
        <Route path="/blog" element={<><Navbar /><Blog /><Footer /></>} />
        <Route path="/testimonials" element={<><Navbar /><Testimonials /><Footer /></>} />
        <Route path="/contests" element={<><Navbar /><Contests /><Footer /></>} />
        <Route path="/contest/:contestId/submit" element={<><Navbar /><ContestSubmission /><Footer /></>} />
        <Route path="/about" element={<><Navbar /><About /><Footer /></>} />
        <Route path="/contact" element={<><Navbar /><Contact /><Footer /></>} />
        <Route path="/login" element={<><Navbar /><Login /><Footer /></>} />
        <Route path="/verify-otp" element={<><Navbar /><VerifyOTP /><Footer /></>} />
        <Route path="/wishlist" element={<><Navbar /><WishlistPage /><Footer /></>} />
        <Route path="/cart" element={<><Navbar /><CartPage /><Footer /></>} />

        {/* User dashboard route */}
        <Route
          path="/user-dashboard"
          element={
            <UserProtectedRoute>
              <Navbar />
              <UserDashboard />
              <Footer />
            </UserProtectedRoute>
          }
        />
        <Route
          path="/book/:id"
          element={
            <>
              <Navbar />
              <BookDetail />
              <Footer />
            </>
          }
        />
        <Route
          path="/reader/:id"
          element={
            <UserProtectedRoute>
              <Reader />
            </UserProtectedRoute>
          }
        />
        <Route
          path="/library"
          element={
            <UserProtectedRoute>
              <Navbar />
              <Library />
              <Footer />
            </UserProtectedRoute>
          }
        />
        
        {/* Orders page route */}
        <Route
          path="/orders"
          element={
            <UserProtectedRoute>
              <Navbar />
              <Library />
              <Footer />
            </UserProtectedRoute>
          }
        />

        {/* eBook Purchase routes */}
        <Route
          path="/ebook-purchase/:id"
          element={
            <UserProtectedRoute>
              <Navbar />
              <EbookPurchase />
              <Footer />
            </UserProtectedRoute>
          }
        />
        <Route
          path="/physical-purchase/:id"
          element={
            <UserProtectedRoute>
              <Navbar />
              <PhysicalPurchase />
              <Footer />
            </UserProtectedRoute>
          }
        />
        <Route
          path="/purchase-success"
          element={
            <>
              <Navbar />
              <PurchaseSuccess />
              <Footer />
            </>
          }
        />
        <Route
          path="/payment-failure"
          element={
            <>
              <Navbar />
              <PaymentFailure />
              <Footer />
            </>
          }
        />

        {/* Admin routes (no Navbar/Footer) */}
        <Route path="/admin/login" element={<Navigate to="/login" replace />} />
        <Route path="/admin/dashboard" element={<ProtectedRoute><AdminLayout><AdminDashboard /></AdminLayout></ProtectedRoute>} />
        <Route path="/admin/books" element={<ProtectedRoute><AdminLayout><AdminBooks /></AdminLayout></ProtectedRoute>} />
        <Route path="/admin/authors" element={<ProtectedRoute><AdminLayout><AdminAuthors /></AdminLayout></ProtectedRoute>} />
        <Route path="/admin/testimonials" element={<ProtectedRoute><AdminLayout><AdminTestimonials /></AdminLayout></ProtectedRoute>} />
        <Route path="/admin/contests" element={<ProtectedRoute><AdminLayout><AdminContests /></AdminLayout></ProtectedRoute>} />
        <Route path="/admin/orders" element={<ProtectedRoute><AdminLayout><AdminOrders /></AdminLayout></ProtectedRoute>} />

        {/* 404 — catch all unmatched routes */}
        <Route path="*" element={<><Navbar /><NotFound /><Footer /></>} />
      </Routes>
    </>
  );
}
