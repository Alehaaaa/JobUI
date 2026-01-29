import SwiftUI

/// A custom view modifier that adds a tracking area to a view to change the cursor
/// based on hover and click state, providing visual feedback for draggable items.
struct DraggableCursorModifier: ViewModifier {
    @State private var isHovering = false
    @State private var isDragging = false

    func body(content: Content) -> some View {
        content
            .onHover { hovering in
                isHovering = hovering
                if hovering {
                    NSCursor.openHand.set()
                } else {
                    NSCursor.arrow.set()
                }
            }
            .gesture(
                DragGesture(minimumDistance: 0)
                    .onChanged { _ in
                        if !isDragging {
                            isDragging = true
                            NSCursor.closedHand.set()
                        }
                    }
                    .onEnded { _ in
                        isDragging = false
                        if isHovering {
                            NSCursor.openHand.set()
                        } else {
                            NSCursor.arrow.set()
                        }
                    }
            )
    }
}

extension View {
    /// Applies a modifier to change the cursor to an open or closed hand,
    /// indicating that the view is draggable.
    func draggableCursor() -> some View {
        self.modifier(DraggableCursorModifier())
    }
}
