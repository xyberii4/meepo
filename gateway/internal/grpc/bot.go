package grpc

import (
	"context"
	"io"

	"github.com/xyberii4/meepo/gateway/internal/grpc/pb"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

type BotService interface {
	JoinMeeting(ctx context.Context, url, name string) (*pb.JoinMeetingResponse, error)
	GetMeetingDetails(ctx context.Context, botID string) (*pb.MeetingDetailsResponse, error)
	LeaveMeeting(ctx context.Context, botID string) (*pb.LeaveMeetingResponse, error)
	Close() error
}

type botClient struct {
	conn   *grpc.ClientConn
	client pb.BotServiceClient
}

func NewBotClient(addr string) (*botClient, error) {
	conn, err := grpc.NewClient(
		addr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		return nil, err
	}

	client := &botClient{
		conn:   conn,
		client: pb.NewBotServiceClient(conn),
	}

	return client, nil
}

// JoinMeeting initiates a streaming RPC to join a meeting.
// returns a channel that receives responses from the server.
func (c *botClient) JoinMeeting(ctx context.Context, url, name string) (<-chan *pb.JoinMeetingResponse, error) {
	stream, err := c.client.JoinMeeting(ctx,
		&pb.JoinMeetingRequest{
			Url:  url,
			Name: name,
		},
	)
	if err != nil {
		return nil, err
	}

	defer stream.CloseSend()

	responses := make(chan *pb.JoinMeetingResponse)

	go func() {
		defer close(responses)

		for {
			resp, err := stream.Recv()

			if err == io.EOF {
				return
			}

			if err != nil {
				return
			}

			responses <- resp
		}
	}()

	return responses, nil
}

func (c *botClient) GetMeetingDetails(ctx context.Context, botID string) (*pb.MeetingDetailsResponse, error) {
	return c.client.GetMeetingDetails(ctx, &pb.MeetingDetailsRequest{
		BotId: botID,
	})
}

func (c *botClient) LeaveMeeting(ctx context.Context, botID string) (*pb.LeaveMeetingResponse, error) {
	return c.client.LeaveMeeting(ctx, &pb.LeaveMeetingRequest{
		BotId: botID,
	})
}

func (c *botClient) Close() error {
	return c.conn.Close()
}
