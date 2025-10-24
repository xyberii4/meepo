package grpc

import (
	"context"
	"net"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/xyberii4/meepo/gateway/internal/grpc/pb"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/status"
	"google.golang.org/grpc/test/bufconn"
)

type mockBotServer struct {
	// forward compatibility
	pb.UnimplementedBotServiceServer
}

func (s *mockBotServer) JoinMeeting(req *pb.JoinMeetingRequest, stream pb.BotService_JoinMeetingServer) error {
	if req.GetBotId() == "" || req.GetMeepoId() == "" || req.GetUrl() == "" {
		return status.Error(codes.InvalidArgument, "missing required fields")
	}

	// stream responses
	responses := []*pb.JoinMeetingResponse{
		{State: pb.JoinMeetingResponse_RECEIVED, Message: "Mock received", BotId: req.GetBotId()},
		{State: pb.JoinMeetingResponse_PENDING, Message: "Mock pending", BotId: req.GetBotId()},
		{State: pb.JoinMeetingResponse_JOINED, Message: "Mock joined", BotId: req.GetBotId()},
	}

	for _, resp := range responses {
		time.Sleep(10 * time.Millisecond)
		if err := stream.Send(resp); err != nil {
			return err
		}
	}

	return nil
}

func (s *mockBotServer) GetMeetingDetails(ctx context.Context, req *pb.MeetingDetailsRequest) (*pb.MeetingDetailsResponse, error) {
	if req.GetBotId() == "" || req.GetMeepoId() == "" {
		return nil, status.Error(codes.InvalidArgument, "missing IDs")
	}

	// mock participants
	return &pb.MeetingDetailsResponse{
		Participants: []*pb.Participant{
			{Name: "Mock User 1"},
			{Name: "Mock User 2"},
		},
	}, nil
}

func (s *mockBotServer) LeaveMeeting(ctx context.Context, req *pb.LeaveMeetingRequest) (*pb.LeaveMeetingResponse, error) {
	if req.GetBotId() == "" || req.GetMeepoId() == "" {
		return nil, status.Error(codes.InvalidArgument, "missing IDs")
	}

	return &pb.LeaveMeetingResponse{
		State:   pb.LeaveMeetingResponse_DONE,
		Message: "Mock left",
	}, nil
}

// initializes mock server and returns connected client.
func setupTestClient(t *testing.T) (BotService, func()) {
	const bufSize = 1024 * 1024
	lis := bufconn.Listen(bufSize)

	s := grpc.NewServer()
	pb.RegisterBotServiceServer(s, &mockBotServer{})

	// start in goroutine
	go func() {
		if err := s.Serve(lis); err != nil {
			t.Logf("Mock server exited with error: %v", err)
		}
	}()

	// to connect to in-memory buffer
	dialer := func(context.Context, string) (net.Conn, error) {
		return lis.Dial()
	}

	// create connection to mock server
	conn, err := grpc.NewClient(
		"passthrough:///bufnet",
		grpc.WithContextDialer(dialer),
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		t.Fatalf("Failed to dial bufnet: %v", err)
	}

	// create client instance
	client := &botClient{
		conn:   conn,
		client: pb.NewBotServiceClient(conn),
	}

	cleanup := func() {
		conn.Close()
		s.Stop()
	}

	return client, cleanup
}

// tests full interaction with mock server.
func TestBotClient_FullLifecycle(t *testing.T) {
	client, cleanup := setupTestClient(t)
	defer cleanup()

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	meepoID := uuid.New().String()
	botID := uuid.New().String()
	url := "http://fake.meeting.url"
	name := "TestBot"

	t.Run("JoinMeeting", func(t *testing.T) {
		responses, err := client.JoinMeeting(ctx, meepoID, botID, url, name)
		if err != nil {
			t.Fatalf("JoinMeeting failed: %v", err)
		}

		expectedStates := []pb.JoinMeetingResponse_State{
			pb.JoinMeetingResponse_RECEIVED,
			pb.JoinMeetingResponse_PENDING,
			pb.JoinMeetingResponse_JOINED,
		}

		idx := 0
		for resp := range responses {
			if idx >= len(expectedStates) {
				t.Fatalf("Received more responses than expected")
			}

			if resp.GetState() != expectedStates[idx] {
				t.Errorf("Unexpected state. Got: %s, Want: %s", resp.GetState(), expectedStates[idx])
			}
			if resp.GetBotId() != botID {
				t.Errorf("Unexpected BotID. Got: %s, Want: %s", resp.GetBotId(), botID)
			}
			t.Logf("Received expected state: %s", resp.GetState())
			idx++
		}

		if idx != len(expectedStates) {
			t.Errorf("Did not receive all expected states. Got: %d, Want: %d", idx, len(expectedStates))
		}
	})

	t.Run("GetMeetingDetails", func(t *testing.T) {
		resp, err := client.GetMeetingDetails(ctx, meepoID, botID)
		if err != nil {
			t.Fatalf("GetMeetingDetails failed: %v", err)
		}

		if len(resp.GetParticipants()) != 2 {
			t.Fatalf("Expected 2 participants, got %d", len(resp.GetParticipants()))
		}
		if resp.GetParticipants()[0].GetName() != "Mock User 1" {
			t.Errorf("Unexpected participant name: %s", resp.GetParticipants()[0].GetName())
		}
		t.Logf("Received participants: %s, %s", resp.GetParticipants()[0].GetName(), resp.GetParticipants()[1].GetName())
	})

	// 4. Act & Assert: LeaveMeeting
	t.Run("LeaveMeeting", func(t *testing.T) {
		resp, err := client.LeaveMeeting(ctx, meepoID, botID)
		if err != nil {
			t.Fatalf("LeaveMeeting failed: %v", err)
		}

		if resp.GetState() != pb.LeaveMeetingResponse_DONE {
			t.Errorf("Unexpected state. Got: %s, Want: %s", resp.GetState(), pb.LeaveMeetingResponse_DONE)
		}
		t.Logf("Received leave state: %s", resp.GetState())
	})
}
